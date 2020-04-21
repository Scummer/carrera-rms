//
//  main.swift
//  btserver
//
//  Created by Thomas Reich on 17.04.20.
//  Copyright © 2020 Thomas Reich. All rights reserved.
//

import CoreBluetooth
import Network

class btserver: NSObject {
    let btscanner = Scanner()
    var listUpdateTimer:Timer? = nil
    var connectedPeripheral:CBPeripheral? = nil
    var selectedService:CBService? = nil
    var selectedCharacteristic:CBCharacteristic? = nil
    var port: NWEndpoint.Port
    var listener: NWListener
    var connection: ServerConnection?
    var command: String
    let allowedCmds = ["Version", "generalQuery", "Reset", "clearCU"]
    
    override init() {
        print("init btserver")
        port = NWEndpoint.Port(rawValue: 8888)!
        listener = try! NWListener(using: .udp, on: port)
        command = ""
        super.init()
        startUDPlistener()
        btscanner.delegate = self
        btscanner.start()
        listUpdateTimer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(btserver.listUpdateTimerFired), userInfo: nil, repeats: true)

    }
    
    func startUDPlistener() {
        print("Server starting...")
        listener.stateUpdateHandler = self.stateDidChange(to:)
        listener.newConnectionHandler = self.didAccept(nwConnection:)
        listener.start(queue: .main)
        NotificationCenter.default.addObserver(self, selector: #selector(self.methodOfReceivedNotification(notification:)), name: Notification.Name("udpdata"), object: nil)
    }
    
    func stateDidChange(to newState: NWListener.State) {
        switch newState {
        case .ready:
            print("Server ready.")
        case .failed(let error):
            print("Server failure, error: \(error.localizedDescription)")
            exit(EXIT_FAILURE)
        default:
            break
        }
    }

    private func didAccept(nwConnection: NWConnection) {
        let connection = ServerConnection(nwConnection: nwConnection)
        self.connection = connection
        connection.start()
        print("server did open connection \(connection.id)")
    }

    @objc func methodOfReceivedNotification(notification: Notification) {
        let writeString = notification.object as! String
        let payload = writeString.split(separator: "&")
        command = String(payload[0])
        var cudata: String = ""
        if let i = allowedCmds.firstIndex(where: {$0 == command}) {
            switch command {
            case "Version":
                cudata = "0"
                command = cudata
            case "Reset":
                cudata = "=10"
            case "generalQuery":
                cudata = "?"
                command = cudata
            default:
                break
            }
        } else {
            cudata = String(payload[0])
        }
        let writeData:Data? = cudata.data(using: String.Encoding.ascii)
        writeDataToSelectedCharacteristic(writeData!)
    }
    
    func writeDataToSelectedCharacteristic(_ data:Data) {
        if let characteristic = selectedCharacteristic {
            var writeType = CBCharacteristicWriteType.withResponse
            if (!characteristic.properties.contains(.write)) {
                writeType = .withoutResponse
            }
            connectedPeripheral?.writeValue(data, for: characteristic, type: writeType)
//            printlog(characteristic, data: data)
        }
    }
    
    @objc func listUpdateTimerFired() {
        for device in btscanner.devices {
            if device.name == "Control_Unit" {
                selectPeripheral(device)
                listUpdateTimer?.invalidate()
                listUpdateTimer = nil
            }
        }
    }
    
    func printlog(_ characteristic:CBCharacteristic, data: Data? = nil) {
        let data = data ?? characteristic.value ?? Data()
        let hexString = data.hexString
        print("UUID \(characteristic.uuid.uuidString)  Value: 0x\(hexString)")
    }
}


extension Data {
    var hexString: String {
        var hex:String = ""
        for byte in self {
            hex += String(format: "%02X", byte)
        }
        return hex
    }
}

extension btserver : CBCentralManagerDelegate {
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        print((peripheral.name ?? "") + ":\n connected")
        peripheral.discoverServices(nil)
    }
    
    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        if let connectedPeripheral = connectedPeripheral {
            print((connectedPeripheral.name ?? "") + ":\n disconnected")
            self.connectedPeripheral = nil
            btscanner.start()
            listUpdateTimer = Timer.scheduledTimer(timeInterval: 0.5, target: self, selector: #selector(btserver.listUpdateTimerFired), userInfo: nil, repeats: true)
        } else {
            print("")
        }
    }
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {}
    
    func selectPeripheral(_ peripheral:CBPeripheral) {
        if peripheral != connectedPeripheral {
            connectPeripheral(peripheral)
        }
    }
    
    func connectPeripheral (_ peripheral:CBPeripheral) {
        self.connectedPeripheral = peripheral
        peripheral.delegate = self
        btscanner.central.connect(peripheral, options: [:])
        btscanner.stop()
    }
    
    func disconnectPeripheral () {
        if let connectedPeripheral = self.connectedPeripheral {
            btscanner.central.cancelPeripheralConnection(connectedPeripheral)
        }
    }
    
}


extension btserver : CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        if let services = peripheral.services {
            for service in services {
                peripheral.discoverCharacteristics(nil, for: service)
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didDiscoverCharacteristicsFor service: CBService, error: Error?) {
        if let characteristics = service.characteristics {
            for characteristic in characteristics {
                if !characteristic.properties.intersection([.indicate, .notify]).isEmpty {
                    connectedPeripheral?.setNotifyValue(true, for: characteristic)
                }
                if !characteristic.properties.intersection([.write, .writeWithoutResponse]).isEmpty {
                    selectedCharacteristic = characteristic
                }
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didUpdateValueFor characteristic: CBCharacteristic, error: Error?) {
        if let ascii = String(data: characteristic.value ?? Data(), encoding: String.Encoding.ascii) {
            var cmdString: String = ""
            if command == "?" || command == "0" {
                cmdString = command + ascii
            } else if command == "prog" {
                return
            } else {
                cmdString = command + "&" + ascii
            }
            self.connection?.send(data: cmdString.data(using: .utf8)!)
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral, didUpdateNotificationStateFor characteristic: CBCharacteristic, error: Error?) {
        let writeString:Data? = "0".data(using: String.Encoding.ascii)
        writeDataToSelectedCharacteristic(writeString!)
    }
}


class Scanner: NSObject {
    
    var central:CBCentralManager
    weak var delegate:CBCentralManagerDelegate?
    var devices:[CBPeripheral] = []
    var rssiForPeripheral:[CBPeripheral:NSNumber] = [:]
    var advDataForPeripheral:[CBPeripheral:[String:Any]] = [:]
    var started:Bool = false
    
    override init() {
        central = CBCentralManager(delegate: nil, queue: nil)
        super.init()
        central.delegate = self
    }
    
    func start() {
        started = true
        devices = []
        startOpportunity()
    }
    
    func startOpportunity() {
        print("Starting to scan")
        if central.state == .poweredOn && started {
            central.scanForPeripherals(withServices: nil, options: [CBCentralManagerScanOptionAllowDuplicatesKey:false])
        }
    }
    
    func stop() {
        started = false
        print("Stopping scanning")
        central.stopScan()
    }
    
    func restart() {
        stop()
        start()
    }
    
}

extension Scanner : CBCentralManagerDelegate {
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        startOpportunity()
    }
    
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        if devices.firstIndex(of: peripheral) == nil {
            devices.append(peripheral)
        }
        rssiForPeripheral[peripheral] = RSSI
        if advDataForPeripheral[peripheral] != nil {
            advDataForPeripheral[peripheral]! += advertisementData
        } else {
            advDataForPeripheral[peripheral] = advertisementData
        }
    }
    
    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        delegate?.centralManager?(central, didConnect: peripheral)
    }
    
    func centralManager(_ central: CBCentralManager, didDisconnectPeripheral peripheral: CBPeripheral, error: Error?) {
        delegate?.centralManager?(central, didDisconnectPeripheral: peripheral, error: error)
    }
}

func += <KeyType, ValueType> (left: inout Dictionary<KeyType, ValueType>, right: Dictionary<KeyType, ValueType>) {
    for (k, v) in right {
        left.updateValue(v, forKey: k)
    }
}

if #available(macOS 10.14, *) {
    btserver()
    RunLoop.main.run()
}

from ble_gattc import GattClientObserver

# TODO:
# Implement handling of all read and discover functions and keep an up to date copy of
# the peer database.

class GattDb(GattClientObserver):
    def on_primary_service_discovery_response(self, gatt_client, event):
        for service in event.services:
            logger.debug('New service uuid: %s, start handle: %02x, end handle: %02x',
                service.uuid, service.start_handle, service.end_handle)

    def on_characteristic_discovery_response(self, gatt_client, event):
        for characteristic in event.characteristics:
            logger.debug('New characteristic uuid: %s, declaration handle: %02x, value handle: %02x',
                    characteristic.uuid, characteristic.handle_decl, characteristic.handle_value)

    def on_descriptor_discovery_response(self, gatt_client, event):
        for descriptor in event.descriptions:
            logger.debug('New descriptor uuid: %s, handle: %02x', descriptor.uuid, descriptor.handle)


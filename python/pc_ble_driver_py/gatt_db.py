from observers import GattClientObserver


# TODO:
# Implement handling of all read and discover functions and keep an up to date copy of
# the peer database.

class GattDb(GattClientObserver):
    def on_primary_service_discovery_response(self, gatt_client, event):
        pass # TODO: Implement

    def on_characteristic_discovery_response(self, gatt_client, event):
        pass # TODO: Implement

    def on_descriptor_discovery_response(self, gatt_client, event):
        pass # TODO: Implement


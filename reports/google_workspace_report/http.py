import requests
from functools import reduce
from operator import getitem
from connect.client import ConnectClient, R

SERVICE_IDS = ["SRVC-9722-3113", "SRVC-5460-5389"]


class GoogleAPIClient(object):
    def __init__(self, connect_client: ConnectClient, api_url, marketplace_id):
        self.api_url = api_url
        self.client = connect_client
        self.marketplace_id = marketplace_id.upper()

    def get_customer_entitlements(self, customer_id):
        headers = {
            "Accept": "application/json",
            "Authorization": self.client.api_key,
        }
        response = requests.get(
            '{}/api/customer_entitlements?marketplace_id={}&customer_id={}'.format(
                self.api_url,
                self.marketplace_id,
                customer_id
            ), headers=headers
        )
        if response.status_code == 200:
            entitlements = response.json()
            return entitlements
        raise GoogleAPIClientError(f'Google Management Settings Error: {response.content}')

    def get_entitlement_offer(self, customer_id, entitlement_id):
        headers = {
            "Accept": "application/json",
            "Authorization": self.client.api_key,
        }
        response = requests.get(
            '{}/api/entitlement_offer?marketplace_id={}&customer_id={}&entitlement_id={}'.format(
                self.api_url,
                self.marketplace_id,
                customer_id,
                entitlement_id
            ), headers=headers
        )
        if response.status_code == 200:
            offer = response.json()
            return offer
        raise GoogleAPIClientError(f'Google Management Settings Error: {response.content}')


def obtain_url_for_service(client):
    query = R()
    query &= R().status.eq('installed')
    query &= R().environment.extension.id.oneof(SERVICE_IDS)
    installation = client.ns('devops').collection('installations').filter(query).first()
    if not installation:
        raise ValueError('The service for the Google Managements Settings was not found.')

    hostname = _get_value(installation, ['environment', 'hostname'])
    domain = _get_value(installation, ['environment', 'domain'])
    url = 'https://' + hostname + '.' + domain
    return url


class GoogleAPIClientError(Exception):
    pass


def _get_value(base, path, default="-"):
    try:
        return reduce(lambda value, path_elem: getitem(value, path_elem), path, base)
    except (IndexError, KeyError, TypeError):
        return default

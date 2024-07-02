# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, CloudBlue
# All rights reserved.
#

from copy import deepcopy

from reports.google_workspace_report.http import GoogleAPIClient, GoogleAPIClientError
from reports.google_workspace_report.entrypoint import (
    calculate_period,
    generate,
    get_price,
    HEADERS, )

PARAMETERS = {
    'date': None,
    'mkp': {
        'all': True,
        'choices': [],
    },
    'status': {
        'all': True,
        'choices': [],
    },
}


def test_generate(monkeypatch, progress, client_factory, response_factory, installation_list, subscription_request,
                  entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress))

    assert len(result) == 1


def test_generate_without_items(monkeypatch, progress, client_factory, response_factory, installation_list,
                                subscription_request, entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    subscription_request['items'] = []
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == '-'


def test_generate_drive_items(monkeypatch, progress, client_factory, response_factory, installation_list,
                              subscription_request, entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    subscription_request['items'].append(subscription_request['items'][0])
    subscription_request['items'][0]['mpn'] = 'GOOGLE_DRIVE_STORAGE'
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Drive Storage'
    assert result[0]['item_mpn'] == 'GOOGLE_DRIVE_STORAGE'


def test_generate_several_items(monkeypatch, progress, client_factory, response_factory, installation_list,
                                subscription_request, entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    subscription_request['items'].append(subscription_request['items'][0])
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Workspace Business Starter Flexible'
    assert result[0]['item_mpn'] == 'GOOGLE_WORKSPACE_BUSINESS_STARTER_FLEXIBLE'


def test_generate_no_google_parameters_in_request(monkeypatch, progress, client_factory, response_factory,
                                                  installation_list, subscription_request, entitlements_request,
                                                  entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    subscription_request['params'] = []
    subscription_request['connection']['provider'] = {}
    subscription_request['events']['created']['at'] = ''
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Workspace Business Starter Flexible'
    assert result[0]['item_mpn'] == 'GOOGLE_WORKSPACE_BUSINESS_STARTER_FLEXIBLE'
    assert result[0]['error_details'] == 'Subscription has missing google parameters.'


def test_generate_google_api_error(monkeypatch, progress, client_factory, response_factory, installation_list,
                                   subscription_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    client = client_factory(responses)
    error_msg = "error message"

    def mock_get_customer_entitlements(*args, **kwargs):
        raise GoogleAPIClientError(error_msg)

    def mock_get_entitlement_offer(*args, **kwargs):
        raise GoogleAPIClientError(error_msg)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['error_details'] == error_msg


def test_generate_all_params(monkeypatch, progress, client_factory, response_factory, installation_list,
                             subscription_request, entitlements_request, entitlement_offer_request):
    responses = []

    parameters = {
        'date': {
            'after': '2020-12-01T00:00:00',
            'before': '2021-01-01T00:00:00',
        },
        'mkp': {
            'all': False,
            'choices': ['MP-123'],
        },
        'connection_type': {
            'all': False,
            'choices': ["test"]},
        'status': {
            'all': False,
            'choices': ['active'],
        },
    }

    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )

    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, parameters, progress))

    assert len(result) == 1


def test_calculate_period():
    assert 'Monthly' == calculate_period(1, 'monthly')
    assert 'Yearly' == calculate_period(1, 'yearly')
    assert '2 Months' == calculate_period(2, 'monthly')
    assert '2 Years' == calculate_period(2, 'yearly')


def test_generate_csv_renderer(monkeypatch, progress, client_factory, response_factory, installation_list,
                               subscription_request, entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    responses.append(
        response_factory(
            query=None,
            value=[subscription_request],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='csv'))

    assert len(result) == 2
    assert result[0] == HEADERS
    assert len(result[0]) == len(HEADERS)
    assert result[0][0] == 'Subscription ID'
    assert progress.call_count == 2
    assert progress.call_args == ((2, 2),)


def test_generate_json_renderer(monkeypatch, progress, client_factory, response_factory, installation_list,
                                subscription_request, entitlements_request, entitlement_offer_request):
    responses = []
    responses.append(
        response_factory(
            query=None,
            value=installation_list
        ),
    )
    responses.append(
        response_factory(
            count=1,
        ),
    )
    asset1 = deepcopy(subscription_request)
    asset2 = deepcopy(subscription_request)
    asset2['id'] = 'AS-123'
    asset2['product']['id'] = 'PRD-2'

    responses.append(
        response_factory(
            query=None,
            value=[asset1, asset2],
        ),
    )
    param_asset2 = {
        'id': '1',
        'name': 't0_f_text',
        'constraints': {
            'reconciliation': True,
        },
    }
    responses.append(
        response_factory(
            value=[],
        ),
    )
    responses.append(
        response_factory(
            value=[param_asset2],
        ),
    )

    def mock_get_customer_entitlements(*args, **kwargs):
        return entitlements_request

    def mock_get_entitlement_offer(*args, **kwargs):
        return entitlement_offer_request

    monkeypatch.setattr(
        GoogleAPIClient, 'get_customer_entitlements', mock_get_customer_entitlements)

    monkeypatch.setattr(
        GoogleAPIClient, 'get_entitlement_offer', mock_get_entitlement_offer)

    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 2
    assert len(result[0]) == len(HEADERS)
    assert result[0]['subscription_id'] == 'AS-2708-7173-4208'
    assert result[1]['subscription_id'] == 'AS-123'
    assert progress.call_count == 1


def test_get_price():
    price = {
        'units': 7,
        'nanos': 120000000,
        'currency_code': 'USD'
    }
    expected = "7.12 USD"
    actual = get_price(price)

    assert actual == expected

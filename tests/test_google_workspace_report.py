# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, CloudBlue
# All rights reserved.
#

from copy import deepcopy

from reports.google_workspace_report.entrypoint import (
    calculate_period,
    generate,
    HEADERS, )

from unittest.mock import patch, MagicMock

from reports.http import obtain_url_for_service

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

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate(mock_obtain_url_for_service, progress, client_factory, response_factory, subscription_request):
    responses = []
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
    result = list(generate(client, PARAMETERS, progress))

    assert len(result) == 1


@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_without_items(mock_obtain_url_for_service,progress, client_factory, response_factory, subscription_request):
    responses = []
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
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == '-'

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_drive_items(progress, client_factory, response_factory, subscription_request):
    responses = []
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
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Drive Storage'
    assert result[0]['item_mpn'] == 'GOOGLE_DRIVE_STORAGE'

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_several_items(progress, client_factory, response_factory, subscription_request):
    responses = []
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
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Workspace Business Starter Flexible'
    assert result[0]['item_mpn'] == 'GOOGLE_WORKSPACE_BUSINESS_STARTER_FLEXIBLE'

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_no_google_parameters_in_request(progress, client_factory, response_factory, subscription_request):
    responses = []
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
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    assert result[0]['item_name'] == 'Google Workspace Business Starter Flexible'
    assert result[0]['item_mpn'] == 'GOOGLE_WORKSPACE_BUSINESS_STARTER_FLEXIBLE'

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_all_params(progress, client_factory, response_factory, subscription_request):
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

    result = list(generate(client, parameters, progress))

    assert len(result) == 1


def test_calculate_period():
    assert 'Monthly' == calculate_period(1, 'monthly')
    assert 'Yearly' == calculate_period(1, 'yearly')
    assert '2 Months' == calculate_period(2, 'monthly')
    assert '2 Years' == calculate_period(2, 'yearly')

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_csv_renderer(progress, client_factory, response_factory, subscription_request):
    responses = []
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
    result = list(generate(client, PARAMETERS, progress, renderer_type='csv'))

    assert len(result) == 2
    assert result[0] == HEADERS
    assert len(result[0]) == 53
    assert result[0][0] == 'Subscription ID'
    assert progress.call_count == 3
    assert progress.call_args == ((2, 2),)

@patch("reports.google_workspace_report.entrypoint.obtain_url_for_service", return_value="https://fake-service.com")
def test_generate_json_renderer(progress, client_factory, response_factory, subscription_request):
    responses = []
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
    client = client_factory(responses)
    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 2
    assert len(result[0]) == 53
    assert result[0]['subscription_id'] == 'AS-2708-7173-4208'
    assert result[0]['vendor_account_id'] == 'VA-610-138'
    assert result[1]['subscription_id'] == 'AS-123'
    assert result[1]['vendor_account_id'] == 'VA-610-138'
    assert progress.call_count == 2


class _FakeGoogleClient:
    """Stands in for GoogleAPIClient so the Google data path can be exercised."""

    ENTITLEMENT_ID = 'SUVs8ePhqWG2TE'

    def get_customer_entitlements(self, customer_id):
        return [{
            'name': f'accounts/A-1/customers/{customer_id}/entitlements/{self.ENTITLEMENT_ID}',
            'provisioning_state': 1,
            'create_time': '2026-01-10T08:00:00Z',
            'commitment_settings': {
                'start_time': '2026-01-10T08:00:00Z',
                'end_time': '2027-01-10T08:00:00Z',
                'renewal_settings': {'enable_renewal': True},
            },
            'parameters': [
                {'name': 'num_units', 'value': {'int64_value': 25}},
                {'name': 'max_units', 'value': {'int64_value': 50}},
                {'name': 'assigned_units', 'value': {'int64_value': 20}},
            ],
        }]

    def get_entitlement_offer(self, customer_id, entitlement_id):
        return {
            'name': 'accounts/A-1/offers/OFFER-1',
            'sku': {
                'name': 'accounts/A-1/skus/1010020027',
                'product': {'name': 'accounts/A-1/products/Google-Apps'},
                'marketing_info': {'display_name': 'Google Workspace Business Standard'},
            },
            'price_by_resources': [{
                'price': {
                    'base_price': {'units': '12', 'nanos': 0, 'currency_code': 'EUR'},
                    'effective_price': {'units': '10', 'nanos': 500000000, 'currency_code': 'EUR'},
                },
            }],
        }


@patch('reports.google_workspace_report.entrypoint.GoogleAPIClient', lambda *a, **kw: _FakeGoogleClient())
@patch('reports.google_workspace_report.entrypoint.obtain_url_for_service', lambda client: 'https://fake-service.com')
def test_generate_fills_google_columns(progress, client_factory, response_factory, subscription_request):
    """Connect returns a product specific parameter id and a separate name, for
    example id 'PRM-550-104-278-0019' with name 'customer_id'. Looking the
    parameters up by id left customer_id and entitlement_id empty, so every row
    reported 'Subscription has missing google parameters.' and '-' in all the
    google_* columns (LITE-35433)."""
    subscription = deepcopy(subscription_request)
    values = {'customer_id': 'Si3BLR4NGdhk0m', 'entitlement_id': _FakeGoogleClient.ENTITLEMENT_ID}
    for param in subscription['params']:
        if param['name'] in values:
            param['value'] = values[param['name']]

    client = client_factory([
        response_factory(count=1),
        response_factory(query=None, value=[subscription]),
    ])

    result = list(generate(client, PARAMETERS, progress, renderer_type='json'))

    assert len(result) == 1
    row = result[0]
    assert row['error_details'] == '-'
    assert row['google_customer_id'] == 'Si3BLR4NGdhk0m'
    assert row['google_entitlement_id'] == _FakeGoogleClient.ENTITLEMENT_ID
    assert row['google_entitlement_status'] == 'active'
    assert row['google_assigned_units'] == 20
    assert row['google_maximum_units'] == 50
    assert row['google_commitment_end_date'] == '2027-01-10T08:00:00Z'
    assert row['google_sku'] == 'accounts/A-1/skus/1010020027'

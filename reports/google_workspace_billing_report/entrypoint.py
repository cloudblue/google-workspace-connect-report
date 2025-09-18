# -*- coding: utf-8 -*-
#
# Copyright (c) 2024, CloudBlue
# All rights reserved.
#
import datetime

from connect.client import R
from dateutil.relativedelta import relativedelta

from reports.http import GoogleAPIClient, GoogleAPIClientError, obtain_url_for_service
from ..utils import convert_to_datetime, get_value, parameter_value, get_price, parameter_value_by_name

HEADERS = (
    'Month Year', 'Subscription ID', 'Subscription External ID', 'Subscription External UUID',
    'Vendor Subscription ID', 'Charge Type', 'Item Name', 'Item MPN',
    'Item Period', 'Quantity', 'Consumption', 'Price', 'Cost', 'Discount',
    'Customer Name', 'Customer External ID', 'Customer Email', 'Tier1 Name', 'Tier1 External ID',
    'Marketplace', 'Hub Name', 'Product Name', 'Charge Date',
    'Subscription Status', 'Subscription Start Date', 'Subscription End Date',
    'Exported At', 'Error Details',
)

GOOGLE_PRODUCTS = ['PRD-861-570-450', 'PRD-550-104-278']
DATE_RANGE_LIMIT_IN_MONTHS = 2

subscriptions_dict = {}
exported_at = datetime.datetime.now()


def generate(
        client=None,
        parameters=None,
        progress_callback=None,
        renderer_type=None,
        extra_context_callback=None,
):
    try:
        _check_report_constraints(parameters)
        url_for_service = obtain_url_for_service(client)
        marketplace_id = parameters['mkp']['choices'][0] if parameters.get('mkp').get('choices') else ""
        google_client = GoogleAPIClient(client, url_for_service, marketplace_id)

        subscriptions = _get_subscriptions(client, parameters)
        total = len(subscriptions)
        progress = 0
        if renderer_type == 'csv':
            yield HEADERS
            progress += 1
            total += 1
            progress_callback(progress, total)

        for subscription in subscriptions:
            orders = _get_orders(subscription, google_client, client, parameters)
            for order in orders:
                if renderer_type == 'json':
                    yield {
                        HEADERS[idx].replace(' ', '_').lower(): value
                        for idx, value in enumerate(_process_line(order))
                    }
                else:
                    yield _process_line(order)

            progress += 1
            progress_callback(progress, total)
    except Exception as e:
        error_row = ['-' for _ in HEADERS]
        error_row[-1] = str(e)
        yield error_row
        progress_callback(1, 1)
        return


def _check_report_constraints(params):
    for product in params.get('product', {}).get('choices'):
        if product not in GOOGLE_PRODUCTS:
            raise ReportException('Not all products are google products')

    date_before = convert_to_datetime(params['date']['before'].replace('Z', ''))
    date_after = convert_to_datetime(params['date']['after'].replace('Z', ''))
    date_range = (date_before.year - date_after.year) * 12 + date_before.month - date_after.month
    if date_range > DATE_RANGE_LIMIT_IN_MONTHS:
        raise ReportException(f'Date range must not exceed {DATE_RANGE_LIMIT_IN_MONTHS}-month range')


def _get_active_subscriptions(client, parameters):
    query = R()
    if parameters.get('product') and parameters['product']['all'] is False:
        query &= R().product.id.oneof(parameters['product']['choices'])
    if parameters.get('date') and parameters['date']['before'] != '':
        query &= R().events.created.at.le(parameters['date']['before'])
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().asset.connection.type.oneof(parameters['connection_type']['choices'])
    query &= R().status.oneof(['active', 'terminating'])
    return client.ns('subscriptions').assets.filter(query)


def _get_terminated_subscriptions(client, parameters):
    query = R()
    query &= R().product.id.oneof(GOOGLE_PRODUCTS)
    if parameters.get('date') and parameters['date']['after'] != '':
        query &= R().updated.ge(parameters['date']['after'])
        query &= R().updated.le(parameters['date']['before'])
    if parameters.get('mkp') and parameters['mkp']['all'] is False:
        query &= R().marketplace.id.oneof(parameters['mkp']['choices'])
    if parameters.get('connection_type') and parameters['connection_type']['all'] is False:
        query &= R().asset.connection.type.oneof(parameters['connection_type']['choices'])
    query &= R().status.oneof(['terminated', 'suspended'])

    return client.ns('subscriptions').assets.filter(query)


def _get_subscriptions(client, parameters):
    subscriptions = list(_get_active_subscriptions(client, parameters))
    terminated = list(_get_terminated_subscriptions(client, parameters))
    subscriptions.extend(terminated)
    return subscriptions


def _get_orders(subscription, google_client, connect_client, params):
    entitlement_id = get_entitlement_id(subscription.get('params', []))
    subscription_id = subscription.get('id')
    google_subscription = _process_google_subscription(subscription, google_client)
    query = R()
    query &= R().updated.le(params['date']['before'])
    query &= R().type.oneof(['purchase', 'cancel', 'change'])

    requests = connect_client.requests.filter(asset__id=subscription_id, status='approved').filter(query).select(
        '-asset.configuration',
        '-asset.marketplace',
        '-asset.contract',
        '-asset.tiers',
        '-activation_key',
        '-template'
    )
    purchase = connect_client.requests.filter(asset__id=subscription_id, status='approved', type='purchase').first()
    # Case where purchase failed for terminated subscription
    if not purchase:
        return []
    purchase_date = purchase.get('effective_date')
    cancel = connect_client.requests.filter(asset__id=subscription_id, status='approved', type='cancel').first()
    cancel_date = None if not cancel else cancel.get('effective_date')

    records = []
    for request in requests:
        effective_date = convert_to_datetime(request['effective_date'])
        record = {}
        record['month_year'] = f'{effective_date.month}-{effective_date.year}'
        record['vendor_subscription_id'] = entitlement_id
        record['subscription'] = subscription
        record['google_subscription'] = google_subscription
        record['quantity'] = request['asset']['items'][0]['quantity']
        record['consumption'] = _get_consumed_value_from_usage(connect_client, subscription)
        record['start_date'] = purchase_date
        record['end_date'] = cancel_date
        start_date = convert_to_datetime(purchase.get('updated'))
        record['charge_date'] = effective_date
        if request['asset']['items'][0]['old_quantity'] == 'unlimited':
            request['asset']['items'][0]['old_quantity'] = -1
        if request['asset']['items'][0]['quantity'] == 'unlimited':
            request['asset']['items'][0]['quantity'] = -1
        if request['type'] == 'purchase':
            purchase_type = parameter_value('purchase_type', request['asset']['params'])
            record['charge_type'] = 'Transfer' if purchase_type == 'Transfer' else 'New Subscription'
        elif request['type'] == 'change':
            less_than_a_year = abs((effective_date - start_date).days) < 365
            record['charge_type'] = 'Change' if less_than_a_year else 'Renewal Change'
            old_quant = int(request['asset']['items'][0]['old_quantity'])
            current_quant = int(request['asset']['items'][0]['quantity'])
            record['quantity'] = current_quant - old_quant
        elif request['type'] == 'cancel':
            record['charge_type'] = 'Cancel'
        records.append(record)

    records = _add_renewals(records, subscription, google_subscription, purchase_date, cancel_date, params, connect_client)

    return records


def _add_renewals(records, subscription, google_subscription, purchase_date, cancel_date, params, connect_client):
    period = subscription.get('billing', {}).get('period', {}).get('uom')
    renewal_dates = _get_renewal_dates(purchase_date, cancel_date, period, params)
    for renewal_date in renewal_dates:
        query = R()
        query &= R().updated.le(renewal_date.isoformat())
        last_order = connect_client.requests.filter(asset__id=subscription.get('id'), status='approved') \
            .filter(query).order_by('-updated').first()
        record = {
            'month_year': f'{renewal_date.month}-{renewal_date.year}',
            'subscription': subscription,
            'google_subscription': google_subscription,
            'charge_type': 'Renewal',
            'charge_date': renewal_date,
            'start_date': purchase_date,
            'end_date': cancel_date,
            'quantity': '-' if not last_order else last_order['asset']['items'][0]['quantity'],
            'consumption': _get_consumed_value_from_usage(connect_client, subscription)
        }
        records.append(record)

    return records

def _get_renewal_dates(purchase_date, cancel_date, period, params):
    renewal_dates = []
    start_date = convert_to_datetime(params['date']['after'].replace('Z', ''))
    end_date = convert_to_datetime(params['date']['before'].replace('Z', ''))
    purchase_start = convert_to_datetime(purchase_date)
    if cancel_date:
        end_date = convert_to_datetime(cancel_date)
    if period == 'yearly':
        difference_year1 = start_date.year - purchase_start.year
        date1 = purchase_start + relativedelta(years=+difference_year1)
        if start_date <= date1 <= end_date and difference_year1 > 0:
            renewal_dates.append(date1)
        if start_date.year != end_date.year:
            difference_year2 = end_date.year - purchase_start.year
            date2 = purchase_start + relativedelta(years=+difference_year2)
            if start_date <= date2 <= end_date and difference_year2 > 0:
                renewal_dates.append(date2)
    if period == 'monthly':
        difference_month1 = (start_date.year - purchase_start.year) * 12 + start_date.month - purchase_start.month
        date1 = purchase_start + relativedelta(months=+difference_month1)
        if start_date <= date1 <= end_date and difference_month1 > 0:
            renewal_dates.append(date1)
        if start_date.month != end_date.month:
            difference_month2 = (end_date.year - purchase_start.year) * 12 + end_date.month - purchase_start.month
            date2 = purchase_start + relativedelta(months=+difference_month2)
            if start_date <= date2 <= end_date and difference_month2 > 0:
                renewal_dates.append(date2)

    return renewal_dates


def _process_google_subscription(subscription, google_client):
    params = subscription.get('params', [])
    google_customer_id = parameter_value('customer_id', params, "")
    entitlement_id = get_entitlement_id(params)

    if google_customer_id not in subscriptions_dict.keys():
        _get_google_subscriptions(google_client, google_customer_id)
    if subscriptions_dict[google_customer_id].get('error'):
        return subscriptions_dict[google_customer_id]
    _fill_subscription_entitlement_offer_data(google_client, google_customer_id, entitlement_id)
    return subscriptions_dict.get(google_customer_id).get(entitlement_id, {})


def _fill_subscription_entitlement_offer_data(google_client, google_customer_id, entitlement_id):
    try:
        entitlement_offer_data = google_client.get_entitlement_offer(google_customer_id, entitlement_id)
    except GoogleAPIClientError as err:
        subscriptions_dict[google_customer_id][entitlement_id] = {'error': str(err)}
        return

    subscriptions_dict[google_customer_id][entitlement_id]['entitlement_data'] = entitlement_offer_data


def _get_google_subscriptions(google_client, google_customer_id):
    try:
        entitlements = google_client.get_customer_entitlements(google_customer_id)
    except GoogleAPIClientError as err:
        subscriptions_dict[google_customer_id] = {'error': str(err)}
        return
    subscriptions_dict[google_customer_id] = _entitlements_as_dict(entitlements)


def _entitlements_as_dict(entitlements):
    result = {}
    for entitlement in entitlements:
        _id = entitlement['name'].split('/')[-1]
        result[_id] = entitlement
    return result


def _process_google_data(google_subscription, charge_type):
    data = {}
    entitlement_data = google_subscription.get('entitlement_data', {})
    sku = entitlement_data.get('sku', {})

    data['product'] = sku.get('product', {}).get('name', '-')
    data['num_units'] = get_google_parameter('num_units', google_subscription.get('parameters', [])).get(
        'value', {}).get('int64_value', '-')
    data['max_units'] = get_google_parameter('max_units', google_subscription.get('parameters', [])).get(
        'value', {}).get('int64_value', '-')
    data['assigned_units'] = get_google_parameter('assigned_units', google_subscription.get('parameters', [])).get(
        'value', {}).get('int64_value', '-')

    # Get price information from price_by_resources
    price_resources = entitlement_data.get('price_by_resources', [])
    if price_resources and len(price_resources) > 0:
        price_resource = price_resources[0]
        price = price_resource.get('price', {})
        
        if charge_type == 'Change':
            price_phases = price_resource.get('price_phases', [])
            phase_price = None
            for phase in price_phases:
                if phase.get('first_period') == 1:
                    phase_price = phase.get('price', {})
                    break

            if phase_price:
                data['effective_price'] = get_price(phase_price.get('base_price', {}))
                data['base_price'] = get_price(phase_price.get('base_price', {}))
            else:
                data['effective_price'] = get_price(price.get('base_price', {}))
                data['base_price'] = get_price(price.get('base_price', {}))

        elif charge_type == 'RenewalChange':
            price_phases = price_resource.get('price_phases', [])
            phase_price = None
            for phase in price_phases:
                if phase.get('first_period') == 13:
                    phase_price = phase.get('price', {})
                    break

            if phase_price:
                data['effective_price'] = get_price(phase_price.get('base_price', {}))
                data['base_price'] = get_price(phase_price.get('base_price', {}))
            else:
                data['effective_price'] = get_price(price.get('base_price', {}))
                data['base_price'] = get_price(price.get('base_price', {}))
        else:
            data['effective_price'] = get_price(price.get('base_price', {}))
            data['base_price'] = get_price(price.get('base_price', {}))
            
        # Get discount as a float value
        data['discount'] = price.get('discount', '-')
    else:
        data['effective_price'] = '-'
        data['base_price'] = '-'
        data['discount'] = '-'
    data['created_time'] = google_subscription.get('create_time', '-')
    data['commitment_start_date'] = google_subscription.get('commitment_settings', {}).get('start_time', '-')
    data['commitment_end_date'] = google_subscription.get('commitment_settings', {}).get('end_time', '-')
    data['error'] = google_subscription.get('error', '-')

    return data


def _get_consumed_value_from_usage(client, subscription):
    try:
        record = client.get(f'/usage/records?asset.id={subscription["id"]}&ordering(-created_time)&limit=1&offset=0')
        if len(record) == 0:
            return '-'
        return record[0].get('usage', '-')
    except Exception:
        return '-'


def _process_line(order):
    subscription = order.get('subscription')
    item_name, item_mpn, item_period = get_item_data(subscription.get('items', []))
    customer_mail = get_google_mail(subscription.get('params', []))
    charge_type = order.get('charge_type')
    google_subscription = order.get('google_subscription')
    google_data = _process_google_data(google_subscription, charge_type)

    return (
        order.get('month_year'),
        subscription.get('id'),
        subscription.get('external_id', '-'),
        subscription.get('external_uid', '-'),
        order.get('vendor_subscription_id', '-'),
        charge_type,
        item_name,
        item_mpn,
        item_period,
        order.get('quantity'),
        order.get('consumption'),
        google_data.get('base_price', '-'),
        google_data.get('effective_price', '-'),
        google_data.get('discount', '-'),
        get_value(subscription.get('tiers', ''), 'customer', 'name'),
        get_value(subscription.get('tiers', ''), 'customer', 'external_id'),
        customer_mail,
        get_value(subscription.get('tiers', ''), 'tier1', 'name'),
        get_value(subscription.get('tiers', ''), 'tier1', 'external_id'),
        subscription.get('marketplace', {}).get('name'),
        get_value(subscription.get('connection', {}), 'hub', 'name'),
        get_value(subscription, 'product', 'name'),
        order.get('charge_date'),
        subscription.get('status'),
        order.get('start_date'),
        order.get('end_date'),
        exported_at,
        google_data.get('error', '-'),
    )


def get_google_parameter(value, params):
    try:
        return list(filter(lambda param: param['name'] == value, params))[0]
    except (IndexError, KeyError, TypeError):
        return {}


def get_entitlement_id(params):
    param_value = parameter_value('entitlement_id', params, "")
    if not param_value:
        return param_value
    entitlement_id = param_value.strip('["]')
    return entitlement_id


def get_item_data(items):
    if len(items) == 0:
        return '-', '-', '-'
    elif len(items) == 1:
        return items[0]['display_name'], items[0]['mpn'], items[0]['period']
    else:
        for item in items:
            if 'GOOGLE_DRIVE_STORAGE' in item.get('mpn'):
                return 'Google Drive Storage', 'GOOGLE_DRIVE_STORAGE', item.get('period')

        return items[0]['display_name'], items[0]['mpn'], items[0]['period']


def get_google_mail(params):
    prefix = parameter_value_by_name('admin_email', params, "")
    domain = parameter_value_by_name('domain', params, "")

    if prefix and domain:
        return f"{prefix.strip()}@{domain.strip()}"
    else:
        return '-'


class ReportException(Exception):
    pass

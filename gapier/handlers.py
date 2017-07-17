#!/usr/bin/env python

import webapp2
import sys
import re
import json
import httplib2
import xmltodict
import string
import random
import urllib
import logging
import time
import zlib
import base64
import md5

from httplib import HTTPException
from collections import OrderedDict

from oauth2client.client import OAuth2WebServerFlow
from google.appengine.api import memcache
from google.appengine.api import users

from gapier import models

class MainHandler(webapp2.RequestHandler):
    def get(self):
        info = models.ClientInfo.get_latest()
        user = users.get_current_user()
        credentials = models.CredentialsInfo.get_latest();
        template_values = {}

        if not info:
            try:
                with open('client_secret.json', 'r') as f:
                    secret_data = json.loads(f.read())
                    template_values["prefill_client_id"] = secret_data["web"]["client_id"];
                    template_values["prefill_client_secret"] = secret_data["web"]["client_secret"];
            except:
                pass

        if user:
            template_values["config_user"] = user.user_id()
            template_values["logout_url"] = users.create_logout_url('/')
            if info:
                template_values["client_url"] = info.client_url
                template_values["client_id"] = info.client_id
                if credentials:
                    template_values["credentials"] = 'ok'
                if user.user_id() != info.config_user:
                    template_values["wrong_user"] = "Expected user with ID " + info.config_user
                    template_values["expected_config_user_email"] = info.config_user_email
        else:
            template_values["login_url"] = users.create_login_url('/')
            if info:
                template_values["expected_config_user_email"] = info.config_user_email

        base64_variables = base64.b64encode(json.dumps(template_values, sort_keys=True, indent=4))

        import os
        import jinja2

        template = jinja2.Environment( loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + '/templates' ),  extensions=['jinja2.ext.autoescape'] ).get_template('index.jinja2')
        self.response.write(template.render({"base64_variables":base64_variables}))

class SetClientHandler(webapp2.RequestHandler):
    def post(self):
        params = json.loads( self.request.body )
        user = users.get_current_user()

        latest = models.ClientInfo.get_latest()
        if latest:
            return self.error(403)
        if not params['client_id'] or not params['client_secret'] or not params['gapier_url']:
            return self.error(409)

        models.ClientInfo.set_new( params['client_id'], params['client_secret'], params['gapier_url'], user.user_id(), user.email() )
        output_result_as_json( self, 'ok');

class StartConnectingHandler(webapp2.RequestHandler):
    def get(self):
        return self.redirect( get_flow().step1_get_authorize_url() )

class OAuth2CallbackHandler(webapp2.RequestHandler):
    def get(self):
        code = self.request.get('code')
        if code:
            info = models.ClientInfo.get_latest()
            credentials = get_flow( info ).step2_exchange( code )

            models.CredentialsInfo.set_new( credentials )

            return self.redirect( '/' )

        else:
            output_result_as_json( self, 'no code returned :( error was: ' + self.request.get('error') )

class ListTokensHandler(webapp2.RequestHandler):
    def get(self):
        if check_invalid_auth( self ): return

        aliases = models.WorksheetToken.get_all()
        aliases.sort(key=lambda x: x.get_token())
        result_data = []
        for alias in aliases:
            is_bundle = 0
            if re.search( 'bundle$', alias.alias.lower() ):
                is_bundle = 1

            lacks_bundle = 1
            if re.search( 'bundle', alias.alias.lower() ):
                lacks_bundle = 0

            alias_data = { 'token' : alias.get_token(), 'access_mode' : alias.get_access_mode(), 'alias' : alias.alias, 'password' : alias.password, 'is_bundle' : is_bundle, 'lacks_bundle' : lacks_bundle }
            result_data.append( alias_data )

        output_as_json( self, result_data )

class GetDocumentListHandler(webapp2.RequestHandler):
    def get(self):
        if check_invalid_auth( self ): return

        document_data = authorized_xml_request_as_dict( 'https://spreadsheets.google.com/feeds/spreadsheets/private/full?max-results=50' )

        output_as_json( self, document_data )

class GetDocumentSheetListHandler(webapp2.RequestHandler):
    def get(self):
        if check_invalid_auth( self ): return

        document_key = self.request.get('spreadsheet_key')
        document_data = authorized_xml_request_as_dict( 'https://spreadsheets.google.com/feeds/worksheets/'+ document_key +'/private/full' )

        entries = document_data['feed']['entry']
        if not type(entries) is list:
            entries = [ entries ]
        result_data = []
        for entry in entries:
            entry_data = { 'title' : entry['title'], 'src' : entry['content']['@src'] }
            result_data.append( entry_data )

        output_as_json( self, result_data )

class AddTokenHandler(webapp2.RequestHandler):
    def post(self):
        if check_invalid_auth( self ): return

        params = json.loads( self.request.body )

        models.WorksheetToken.add( params['alias'], params['listfeed_url'], params['spreadsheet_key'], params['password'], params['access_mode'] )

        output_result_as_json( self, 'ok');

class RemoveTokenHandler(webapp2.RequestHandler):
    def post(self):
        if check_invalid_auth( self ): return

        params = json.loads( self.request.body )
        token = models.WorksheetToken.get_for_token( params['token'] )
        token.remove();

        output_result_as_json( self, 'ok');

class AddBundleSheetHandler(webapp2.RequestHandler):
    def post(self):
        if check_invalid_auth( self ): return

        params = json.loads( self.request.body )

        from_token = models.WorksheetToken.get_for_token( params['worksheet_token'] )

        if not from_token:
            return output_result_as_json( self, 'Invalid token');
        if not from_token.spreadsheet_key:
            return output_result_as_json( self, 'No spreadsheet_key in token');

        columns_string = params['columns']
        columns = re.compile(r'\s*\,\s*').split( columns_string )

        add_url = 'https://spreadsheets.google.com/feeds/worksheets/' + from_token.spreadsheet_key + '/private/full';

        result = add_empty_sheet_to_spreadsheet( add_url, params['title'], 1, len(columns) )

        listfeed_url = result['entry']['content']['@src']

        token = models.WorksheetToken.add( params['alias'], listfeed_url, from_token.spreadsheet_key, params['password'], params['access_mode'] )

        add_token_key_to_bundle_spreadsheet( params['key'], token.get_token(), from_token.listfeed_url )

        cellsfeed_url = listfeed_url.replace('/list/', '/cells/', 1);
        replace_spreadsheet_row_values( cellsfeed_url, 1, columns )

        output_result_as_json( self, 'ok' );

class CreateBundleHandler(webapp2.RequestHandler):
    def post(self):
        if check_invalid_auth( self ): return

        params = json.loads( self.request.body )

        from_token = models.WorksheetToken.get_for_token( params['worksheet_token'] )

        if not from_token:
            return output_result_as_json( self, 'Invalid token');
        if not from_token.spreadsheet_key:
            return output_result_as_json( self, 'No spreadsheet_key in token');

        columns = [ 'Sheet key', 'Token' ];

        add_url = 'https://spreadsheets.google.com/feeds/worksheets/' + from_token.spreadsheet_key + '/private/full';

        result = add_empty_sheet_to_spreadsheet( add_url, params['title'], 1, len(columns) )

        listfeed_url = result['entry']['content']['@src']

        bundle_alias = params['alias']
        if not re.compile(r'.*bundle$').match( bundle_alias ):
            bundle_alias = bundle_alias + '-bundle'

        token = models.WorksheetToken.add( bundle_alias, listfeed_url, from_token.spreadsheet_key, params['password'], 'read-only' )

        cellsfeed_url = listfeed_url.replace('/list/', '/cells/', 1);
        replace_spreadsheet_row_values( cellsfeed_url, 1, columns )

        newly_bundled_alias = bundle_alias + '-' + from_token.alias

        newly_bundled_token = models.WorksheetToken.add( newly_bundled_alias, from_token.listfeed_url, from_token.spreadsheet_key, from_token.password, from_token.access_mode )

        add_token_key_to_bundle_spreadsheet( from_token.alias, newly_bundled_token.get_token(), listfeed_url )

        output_result_as_json( self, 'ok' );

def add_empty_sheet_to_spreadsheet( add_url, title, rows_count, columns_count ):
    entry = OrderedDict()
    entry['@xmlns'] = 'http://www.w3.org/2005/Atom'
    entry['@xmlns:gs'] = "http://schemas.google.com/spreadsheets/2006"
    entry['title'] = title;
    entry['gs:rowCount'] = rows_count;
    entry['gs:colCount'] = columns_count;

    entry_dict = OrderedDict([ ( 'entry', entry ) ] )
    entry_xml = xmltodict.unparse( entry_dict ).encode('utf-8')

    content = make_authorized_request( add_url, None, 'POST', entry_xml )
    return xmltodict.parse( content )

def add_token_key_to_bundle_spreadsheet( sheet_key, token, listfeed_url ):
    entry = OrderedDict()
    entry['gsx:sheetkey'] = unicode( sheet_key )
    entry['gsx:token'] = unicode( token )
    entry_xml = entry_to_utf8_gsx_xml( entry )
    make_authorized_request( listfeed_url, None, 'POST', entry_xml )

def replace_spreadsheet_row_values( cellsfeed_url, row_number, column_values, use_raw_values=False ):
    for index, column in enumerate(column_values, start=1):
        cell = 'R' + str(row_number) + 'C' + str(index)
        cell_url = cellsfeed_url + '/' + cell

        value = str(column)
        if not use_raw_values:
            value = "'" + value

        entry = OrderedDict()
        entry['@xmlns'] = 'http://www.w3.org/2005/Atom'
        entry['@xmlns:gs'] = "http://schemas.google.com/spreadsheets/2006"
        entry['id'] = cell_url
        entry['link'] = OrderedDict()
        entry['link']['@rel'] = 'edit'
        entry['link']['@type'] = 'application/atom+xml'
        entry['link']['@href'] = cell_url
        entry['gs:cell'] = OrderedDict()
        entry['gs:cell']['@row'] = str(row_number)
        entry['gs:cell']['@col'] = str(index)
        entry['gs:cell']['@inputValue'] = unicode( value )
        entry_dict = OrderedDict([ ( 'entry', entry ) ] )
        entry_xml = xmltodict.unparse( entry_dict ).encode('utf-8')

        make_authorized_request( cell_url, None, 'PUT', entry_xml, { 'If-None-Match' : 'replace' } )

class FetchHandler(webapp2.RequestHandler):
    def post_and_get(self):
        result = get_worksheet_list_dict_or_error_for_webapp( self, required_access_mode='read-only' )

        if 'error' in result:
            return result['error']

        list_dict = result['dict']

        entries = []

        if not 'feed' in list_dict or not 'entry' in list_dict['feed']:
            return output_as_json( self, entries )

        namere = re.compile('^gsx\:(.*)$')

        for entry in list_dict['feed']['entry']:
            data = {}
            for key in entry.keys():
                match = namere.match( key )
                if match:
                    data[ match.group(1) ] = unicode( entry[ key ] or "" )

            entries.append( data )

        output_as_json( self, entries )

    def post(self):
        return self.post_and_get()

    def get(self):
        return self.post_and_get()

class UpdateRowHandler(webapp2.RequestHandler):
    def post_and_get(self):
        return generic_add_update_remove_handler( self, update_mode=True );

    def post(self):
        return self.post_and_get()

    def get(self):
        return self.post_and_get()

class AddRowHandler(webapp2.RequestHandler):
    def post_and_get(self):
        return generic_add_update_remove_handler( self, add_mode=True );

    def post(self):
        return self.post_and_get()

    def get(self):
        return self.post_and_get()

class AddOrUpdateRowHandler(webapp2.RequestHandler):
    def post_and_get(self):
        return generic_add_update_remove_handler( self, add_mode=True, update_mode=True );

    def post(self):
        return self.post_and_get()

    def get(self):
        return self.post_and_get()

class RemoveRowHandler(webapp2.RequestHandler):
    def post_and_get(self):
        return generic_add_update_remove_handler( self, remove_mode=True );

    def post(self):
        return self.post_and_get()

    def get(self):
        return self.post_and_get()

def output_as_json( webapp, data ):
    if webapp.request.get('callback'):
        webapp.response.content_type = 'application/javascript'
        webapp.response.write(webapp.request.get('callback') + '(' + json.dumps(data, sort_keys=True, indent=4) + ');' )
    else:
        webapp.response.content_type = 'application/json'
        webapp.response.write(json.dumps(data, sort_keys=True, indent=4))

def output_result_as_json( webapp, result ):
    output_as_json( webapp, { 'result' : result } )

def generic_add_update_remove_handler( webapp, update_mode=False, add_mode=False, remove_mode=False ):

    if add_mode:
        allow_empty = True
    else:
        allow_empty = False

    result = get_match_data_or_error_for_webapp( webapp, allow_empty )

    if 'error' in result:
        return result['error']

    match_data = result['data']

    if update_mode and not add_mode:
        allow_empty = False
    else:
        allow_empty = True

    result = get_set_data_or_error_for_webapp( webapp, allow_empty )

    if 'error' in result:
        return result['error']

    set_data = result['data']

    if add_mode and not update_mode:
        if not match_data:
            result = get_worksheet_list_dict_or_error_for_webapp( webapp, required_access_mode='add-only', headers_only=True )
        else:
            result = get_worksheet_list_dict_or_error_for_webapp( webapp, required_access_mode='add-only' )
    else:
        result = get_worksheet_list_dict_or_error_for_webapp( webapp )

    if 'error' in result:
        return result['error']

    list_dict = result['dict']

    # TODO: 409 Conflict if match_data contains gsx: entries that do not exist in non-empty list_dict
    # TODO: 409 Conflict if set_data contains gsx: entries that do not exist in non-empty list_dict

    if match_data:
        found_entries = find_matching_list_dict_entries_for_data( list_dict, match_data )
    else:
        found_entries = None

    if not found_entries:
        if not add_mode:
            return custom_error( webapp, 404, 'Matching rows not found.')

        entry = OrderedDict()

        for data_list in [ match_data, set_data ]:
            for data in data_list:
                entry[ data['gsx'] ] = unicode( data['value'] or "" )

        entry_xml = entry_to_utf8_gsx_xml( entry )

        for link in list_dict['feed']['link']:
            if link['@rel'] == 'http://schemas.google.com/g/2005#post':
                make_authorized_request( link['@href'], None, 'POST', entry_xml )

        output_result_as_json( webapp, 'DONE: Row was added.')

    elif update_mode:
        update_count = 0

        for entry in found_entries:
            needs_update = False
            for match in set_data:
                for key in entry.keys():
                    if key == match['gsx']:
                        if unicode( entry[key] or "" ) != unicode( match['value'] or "" ):
                            needs_update = True
                        entry[key] = unicode( match['value'] or "" )
                        break

            if not needs_update:
                continue

            update_count += 1
            for link in entry['link']:
                if link['@rel'] == 'edit':
                    entry_xml = entry_to_utf8_gsx_xml( entry )
                    make_authorized_request( link['@href'], None, 'PUT', entry_xml )

        output_result_as_json( webapp, 'DONE: ' + str( update_count ) + ' of ' + str( len( found_entries ) ) + ' rows required an update.')

    elif remove_mode:
        remove_count = 0

        for entry in found_entries:
            remove_count += 1

            for link in entry['link']:
                if link['@rel'] == 'edit':
                    entry_xml = entry_to_utf8_gsx_xml( entry )
                    make_authorized_request( link['@href'], None, 'DELETE', entry_xml )

        output_result_as_json( webapp, 'DONE: ' + str( remove_count ) + ' rows were removed.')

    else:
        return custom_error( webapp, 409, 'Matching rows already exist.')

class TrimRowsHandler(webapp2.RequestHandler):
    def post(self):
        result = get_validate_data_or_error_for_webapp( self )

        if 'error' in result:
            return result['error']

        validate_data = result['data']

        result = get_worksheet_list_dict_or_error_for_webapp( self )

        if 'error' in result:
            return result['error']

        list_dict = result['dict']

        removed_count = 0
        preserved_count = 0

        signature_types = {}
        valid_signatures = {}

        for match_data in validate_data:
            signature_type_parts = []
            signature_parts = []

            for match in match_data:
                signature_type_parts.append( match['gsx'] )
                signature_parts.append( unicode( match['value'] or "" ) )

            signature_type = ':-:!:-:'.join( signature_type_parts )
            signature = ':-:!:-:'.join( signature_parts )

            if signature_type not in valid_signatures:
                signature_types[ signature_type ] = signature_type_parts
                valid_signatures[ signature_type ] = {}

            valid_signatures[ signature_type ][ signature ] = True

        for entry in list_dict['feed']['entry']:
            entry_match_found = False

            for signature_type in signature_types.keys():
                signature_type_parts = signature_types[ signature_type ]
                signature_parts = []

                for gsx in signature_type_parts:
                    for key in entry.keys():
                        if key == gsx:
                            signature_parts.append( unicode( entry[key] or "" ) )
                            break

                signature = ':-:!:-:'.join( signature_parts )

                if signature in valid_signatures[ signature_type ]:
                    entry_match_found = True

            if not entry_match_found:
                removed_count += 1
                for link in entry['link']:
                    if link['@rel'] == 'edit':
                        entry_xml = entry_to_utf8_gsx_xml( entry )
                        make_authorized_request( link['@href'], None, 'DELETE', entry_xml )
            else:
                preserved_count += 1

        output_result_as_json( self, 'DONE: ' + str( removed_count ) + ' of ' + str( preserved_count + removed_count ) + ' rows were removed.')

def entry_to_utf8_gsx_xml( entry ):
    entry['@xmlns'] = 'http://www.w3.org/2005/Atom'
    entry['@xmlns:gsx'] = 'http://schemas.google.com/spreadsheets/2006/extended'
    entry['@xmlns:gd'] = "http://schemas.google.com/g/2005"
    entry_dict = OrderedDict([ ( 'entry', entry ) ] )
    xml_entry = xmltodict.unparse( entry_dict )
    return xml_entry.encode('utf-8')

def find_matching_list_dict_entries_for_data( list_dict, match_data ):
    found_entries = []

    for entry in list_dict['feed']['entry']:
        match_valid = True
        for match in match_data:
            found_match = False
            for key in entry.keys():
                if key == match['gsx']:
                    if unicode( entry[key] or "" ) == unicode( match['value'] or "" ):
                        found_match = True
                    else :
                        break

            if not found_match:
                match_valid = False
                break
        if match_valid:
            found_entries.append( entry )

    return found_entries

def get_match_data_or_error_for_webapp( webapp, allow_empty ):
    return _get_data_or_error_for_webapp( webapp, 'match', allow_empty )

def get_set_data_or_error_for_webapp( webapp, allow_empty ):
    return _get_data_or_error_for_webapp( webapp, 'set', allow_empty )

def _get_data_or_error_for_webapp( webapp, prefix, allow_empty=None ):
    match_list = []
    match_json = webapp.request.get( prefix + '_json')
    if match_json:
        try:
            match_data = json.loads( match_json )
            for key in match_data.keys():
                match_list.append( { 'column' : key, 'value' : match_data[key] } )
        except:
            return { 'error' : custom_error( webapp, 400, 'Failed to parse provided ' + prefix + '_json.' ) }
    else:
        match_columns = webapp.request.get( prefix + '_columns')
        match_values = webapp.request.get( prefix + '_values')

        if match_columns:
            columns = re.compile(r'\s*\,\s*').split( match_columns )
            if not match_values:
                match_values = ''
            values = string.split( match_values, ',' )

            for i in range( len( columns )):
                if len( values ) <= i:
                    values.append('')
                match_list.append( { 'column' : columns[i], 'value' : values[i] } )

    for match in match_list:
        gsx = transform_column_name_to_gsx_compatible_format( match['column'] )
        if gsx:
            match['gsx'] = 'gsx:' + gsx
        else:
            return { 'error' : custom_error( webapp, 400, 'Invalid ' + prefix + ' column: ' + match['column'] ) }

    if not match_list and not allow_empty:
        return { 'error' : custom_error( webapp, 400, 'No valid ' + prefix + ' instructions found.' ) }

    return { 'data' : match_list }

def get_validate_data_or_error_for_webapp( webapp ):

    validate_list = []
    validate_json = webapp.request.get('validate_json')
    if validate_json:
        try:
            validate_data = json.loads( validate_json )
            for row in validate_data:
                row_list = []
                for key in row.keys():
                    row_list.append( { 'column' : key, 'value' : row[key] } )
                validate_list.append( row_list )
        except:
            return { 'error' : custom_error( webapp, 400, 'Failed to parse provided validate_json.' ) }
    else:
        validate_columns = webapp.request.get( 'validate_columns')
        validate_values = webapp.request.params.getall( 'validate_values')

        if not validate_values:
            validate_values = webapp.request.params.getall( 'validate_values[]')

        if not validate_values:
            return { 'error' : custom_error( webapp, 400, 'Refusing to trim with no found values.' ) }

        if validate_columns:
            columns = re.compile(r'\s*\,\s*').split( validate_columns )

            for row in validate_values:
                row_list = []
                values = string.split( row, ',' )
                for i in range( len( columns )):
                    if len( values ) <= i:
                        values.append('')
                    row_list.append( { 'column' : columns[i], 'value' : values[i] } )
                validate_list.append( row_list )

    for row_list in validate_list:
        for match in row_list:
            gsx = transform_column_name_to_gsx_compatible_format( match['column'] )
            if gsx:
                match['gsx'] = 'gsx:' + gsx
            else:
                return { 'error' : custom_error( webapp, 400, 'Invalid validate column: ' + match['column'] ) }

    if not validate_list:
        return { 'error' : custom_error( webapp, 400, 'No valid validate instructions found.' ) }

    return { 'data' : validate_list }

def transform_column_name_to_gsx_compatible_format( name ):
    compatible_name = name.lower()
    compatible_name = re.compile(r'^[^a-z]*').sub( '', compatible_name )
    compatible_name = re.compile(r'[^a-z0-9\.\-]*').sub('', compatible_name )
    return compatible_name;

def get_worksheet_list_dict_or_error_for_webapp( webapp, required_access_mode='full', headers_only=False ):
    token = models.WorksheetToken.get_for_token( webapp.request.get('worksheet_token') )

    acceptable_staleness = webapp.request.get('accept_staleness')
    try:
        acceptable_staleness = int( acceptable_staleness )
    except:
        acceptable_staleness = 0

    if not token:
        return { 'error' : custom_error( webapp, 404, 'A valid worksheet_token is required.' ) }

    access_mode = token.get_access_mode();
    if access_mode != 'full':
        if required_access_mode != access_mode:
            return { 'error' : custom_error( webapp, 404, 'A worksheet_token with ' + required_access_mode + ' rights is required. This token has only ' + access_mode + ' rights.'  ) }

    if headers_only:
        # I think headers can be cached indefinitely, but let's settle for 10 minutes
        list_dict = authorized_xml_request_as_dict( token.listfeed_url + '?max-results=1', acceptable_staleness=600 )
        if 'entry' in list_dict['feed']:
            del list_dict['feed']['entry']
    else:
        list_dict = authorized_xml_request_as_dict( token.listfeed_url, acceptable_staleness=acceptable_staleness )

    if not list_dict:
        return { 'error' : webapp.error(500) }

    if not type( list_dict ) is dict:
        return { 'error' : webapp.error(500) }

    if not 'feed' in list_dict:
        return { 'error' : webapp.error(500) }

    if not 'entry' in list_dict['feed']:
        list_dict['feed']['entry'] = []

    if not type( list_dict['feed']['entry'] ) is list:
        list_dict['feed']['entry'] = [ list_dict['feed']['entry'] ]

    return { 'dict' : list_dict }

def get_flow( info=False ):
    if not info:
        info = models.ClientInfo.get_latest()
    return OAuth2WebServerFlow(
            client_id=info.client_id,
            client_secret=info.client_secret,
            scope='profile https://spreadsheets.google.com/feeds',
            approval_prompt='force',
            access_type='offline',
            redirect_uri=info.client_url + '/oauth2callback' )

def make_authorized_request( uri, credentials=None, method='GET', body=None, custom_headers=None ):
    timeouts = [ 17, 8, 4 ]

    if method == 'POST':
        timeouts = [ 29 ]

    while timeouts:
        timeout = timeouts.pop()
        try:
            return make_authorized_request_attempt( uri, credentials=credentials, method=method, body=body, timeout=timeout, custom_headers=custom_headers )
        except HTTPException:
            logging.info( "An attempt to " +method+ " to " +uri+ " timed out in " +str(timeout)+ " seconds." )

    logging.error("All attempts to " +method+ " to " +uri+ " timed out.")
    return ""

def make_authorized_request_attempt( uri, credentials=None, method='GET', body=None, timeout=10, custom_headers=None ):
    if not credentials:
        credentials = models.CredentialsInfo.get_valid_credentials()

    http = httplib2.Http( timeout=timeout )
    http = credentials.authorize( http )

    headers = { 'GData-Version' : '3.0' }
    if custom_headers:
        for header in custom_headers:
            headers[header] = custom_headers[header]

    if method == 'GET':
        data = None

        compressed_data = memcache.get( 'jsoncontent:'+str(uri) )

        if compressed_data is not None:
            data = json.loads( zlib.decompress( compressed_data ) )

        if data is not None:
            headers['If-None-Match'] = data['etag'];

        resp, content = http.request( uri, headers=headers )
        if resp['status'] == '200':
            if 'etag' in resp and resp['etag']:
                try:
                    memcache.set( 'jsoncontent:'+str(uri), zlib.compress( json.dumps( { 'etag' : resp['etag'], 'content' : content } ) ) )

                except:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logging.error(exc_value)

            return content
        elif resp['status'] == '304':
            return data['content']
        else:
            logging.error("Received unexpected return from authorized request. Response and Content to follow:")
            logging.error( resp )
            logging.error( content )
            return ""

    headers['Content-Type'] = 'application/atom+xml'

    resp, content = http.request( uri, method=method, body=body, headers=headers )

    return content

def authorized_xml_request_as_dict( uri, credentials=None, acceptable_staleness=0 ):
    if acceptable_staleness > 0:
        data = memcache.get( "dictjson:" + uri )
        if data is not None:
            data = json.loads( zlib.decompress( data ) )
            if time.time() < int( data['gmtime'] ) + acceptable_staleness:
                print "Serving cached version because of acceptable_staleness."
                return data['content']

    content = make_authorized_request( uri, credentials )

    parsed_content = content_to_dict(content)

    try:
        if acceptable_staleness > 0:
            memcache.set( "dictjson:" + uri, zlib.compress(json.dumps( { 'content' : parsed_content, 'gmtime' : time.time() } )) )
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error(exc_value)

    return parsed_content

def content_to_dict( content ):
    digest = md5.md5(content).hexdigest();
    data = memcache.get( "parseddictjson:" + digest )

    if data is not None:
        pickled_content = zlib.decompress( data )
        parsed_content = json.loads( pickled_content )
        return parsed_content

    print "Missed content dict cache lookup."
    parsed_content = xmltodict.parse( content )

    pickled_content = json.dumps( parsed_content )
    compressed_content = zlib.compress( pickled_content )
    memcache.set( "parseddictjson:" + digest, compressed_content );

    # return json parsed version so we always get dict without OrderedDicts
    return json.loads( pickled_content )

def authorized_json_request_as_dict( uri, credentials=None ):
    content = make_authorized_request( uri, credentials )
    return json.loads( content )

def check_invalid_auth( rh, info=False ):
    user = users.get_current_user()
    if not user:
        return rh.error(403)
    if not info:
        info = models.ClientInfo.get_latest()
    if not info or not info.config_user:
        return rh.error(403)
    if user.user_id() != info.config_user:
        return rh.error(403)
    return False


def custom_error( webapp, code, explanation ):
    webapp.error( code )
    return webapp.response.write( explanation )

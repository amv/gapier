#!/usr/bin/env python

import webapp2
import jinja2
import os
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
import pickle
import base64

from httplib import HTTPException
from collections import OrderedDict

from oauth2client.client import OAuth2WebServerFlow
from google.appengine.api import memcache
from google.appengine.api import users

from gapier import models

JINJA_ENVIRONMENT = jinja2.Environment( loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + '/templates' ), extensions=['jinja2.ext.autoescape'] )

class MainHandler(webapp2.RequestHandler):
    def get(self):
        info = models.ClientInfo.get_latest()
        user = users.get_current_user()
        credentials = models.CredentialsInfo.get_latest();
        template_values = {}

        if user:
            template_values["config_user"] = user.user_id()
            template_values["logout_url"] = users.create_logout_url('/')
            if info:
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

        template = JINJA_ENVIRONMENT.get_template('index.jinja2')
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
            alias_data = { 'token' : alias.get_token(), 'access_mode' : alias.get_access_mode(), 'alias' : alias.alias, 'password' : alias.password }
            result_data.append( alias_data )

        output_as_json( self, result_data )

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

        models.WorksheetToken.add( params['alias'], params['listfeed_url'], params['password'], params['access_mode'] )

        output_result_as_json( self, 'ok');

class FetchHandler(webapp2.RequestHandler):
    def post_and_get(self):
        result = get_worksheet_list_dict_or_error_for_webapp( self, required_access_mode='read-only' )

        if 'error' in result:
            return result['error']

        list_dict = result['dict']

        entries = []

        for entry in list_dict['feed']['entry']:
            data = {}
            for key in entry.keys():
                match = re.compile('^gsx\:(.*)$').match( key )
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

def get_worksheet_list_dict_or_error_for_webapp( webapp, required_access_mode='full' ):
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

    list_dict = authorized_xml_request_as_dict( token.listfeed_url, acceptable_staleness=acceptable_staleness )

    if not list_dict:
        return { 'error' : webapp.error(500) }

    if not type( list_dict ) is OrderedDict:
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

def make_authorized_request( uri, credentials=None, method='GET', body=None, acceptable_staleness=0 ):
    timeouts = [ 17, 8, 4 ]

    if method == 'POST':
        timeouts = [ 29 ]

    while timeouts:
        timeout = timeouts.pop()
        try:
            return make_authorized_request_attempt( uri, credentials=credentials, method=method, body=body, timeout=timeout, acceptable_staleness=acceptable_staleness )
        except HTTPException:
            logging.info( "An attempt to " +method+ " to " +uri+ " timed out in " +str(timeout)+ " seconds." )

    logging.error("All attempts to " +method+ " to " +uri+ " timed out.")
    return ""

def make_authorized_request_attempt( uri, credentials=None, method='GET', body=None, timeout=10, acceptable_staleness=0 ):
    if not credentials:
        credentials = models.CredentialsInfo.get_valid_credentials()

    http = httplib2.Http( timeout=timeout )
    http = credentials.authorize( http )

    headers = { 'GData-Version' : '3.0' }

    if method == 'GET':
        data = None
        compressed_data = memcache.get( uri )

        if compressed_data is not None:
            data = pickle.loads( zlib.decompress( compressed_data ) )

        if data is not None:
            headers['If-None-Match'] = data['etag'];

        resp, content = http.request( uri, headers=headers )
        if resp['status'] == '200':
            if 'etag' in resp and resp['etag']:
                try:
                    memcache.set( uri, zlib.compress( pickle.dumps( { 'etag' : resp['etag'], 'content' : content } ) ) )
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
        data = memcache.get( "dict:" + uri )
        if data is not None:
            data = pickle.loads( zlib.decompress( data ) )
            if time.time() < int( data['gmtime'] ) + acceptable_staleness:
                return data['content']

    content = make_authorized_request( uri, credentials, acceptable_staleness=acceptable_staleness )

    parsed_content = xmltodict.parse( content )

    try:
        if acceptable_staleness > 0:
            memcache.set( "dict:" + uri, zlib.compress(pickle.dumps( { 'content' : parsed_content, 'gmtime' : time.time() } )) )
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.error(exc_value)

    return parsed_content

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

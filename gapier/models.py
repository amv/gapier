#!/usr/bin/env python


from google.appengine.ext import ndb
import httplib2
import string
import logging

GLOBAL_ANCESTOR = ndb.Key( 'Gapier', 'Ancestor' )

class ClientInfo(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    client_id = ndb.StringProperty(indexed=False)
    client_secret = ndb.StringProperty(indexed=False)
    client_url = ndb.StringProperty(indexed=False)
    config_user = ndb.StringProperty(indexed=False)
    config_user_email = ndb.StringProperty(indexed=False)

    @classmethod
    def set_new(cls, client_id, client_secret, client_url, config_user, config_user_email ):
        info = ClientInfo( parent=GLOBAL_ANCESTOR, client_id=client_id, client_secret=client_secret, client_url=client_url, config_user=config_user, config_user_email=config_user_email )
        info.put();

    @classmethod
    def get_latest(cls):
        latest = cls.query( ancestor=GLOBAL_ANCESTOR ).order(-cls.created_date).fetch(1)
        for item in latest:
            return item
        return False

class CredentialsInfo(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    credentials = ndb.PickleProperty(indexed=False)

    @classmethod
    def set_new(cls, credentials ):
        info = CredentialsInfo( parent=GLOBAL_ANCESTOR, credentials=credentials )
        info.put()

    @classmethod
    def get_latest(cls):
        latest = cls.query( ancestor=GLOBAL_ANCESTOR ).order(-cls.created_date).fetch(1)
        for item in latest:
            return item
        return False

    @classmethod
    def get_valid_credentials(cls):
        latest = cls.get_latest()
        if not latest:
            return False
        credentials = latest.credentials
        if credentials.access_token_expired:
            cls.refresh_credentials( credentials )
            latest.credentials = credentials
            latest.put()
            return credentials
        else:
            return credentials

    @classmethod
    def refresh_credentials(cls, credentials):
        http = httplib2.Http()
        credentials.refresh( http );

class WorksheetToken(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    alias = ndb.StringProperty(indexed=True)
    listfeed_url = ndb.StringProperty(indexed=False)
    password = ndb.StringProperty(indexed=False)
    access_mode = ndb.StringProperty(indexed=False)

    def get_token(self):
        if self.password:
            return self.alias + ':' + self.password
        return self.alias

    def get_access_mode(self):
        if self.access_mode:
            return self.access_mode
        return 'full'

    @classmethod
    def get_all(cls):
        return WorksheetToken.query().fetch(999)

    @classmethod
    def add(cls, alias, listfeed_url, password='', access_mode='full'):
        new = WorksheetToken( parent=GLOBAL_ANCESTOR, alias=alias, listfeed_url=listfeed_url, password=password, access_mode=access_mode )
        new.put()

    @classmethod
    def get_for_token(cls, token):
        parts = string.split( token, ':' )
        if len(parts) < 2:
            return False
        find_alias = parts[0]
        match_password = parts[1]

        if not find_alias:
            return False

        found_object = cls.query( cls.alias == find_alias, ancestor=GLOBAL_ANCESTOR ).get()

        if not found_object:
            logging.debug('alias not found')
            return False

        if not found_object.password == match_password:
            logging.debug('password mismatch')
            return False

        return found_object

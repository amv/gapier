#!/usr/bin/env python


from google.appengine.ext import ndb

class ClientInfo(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    client_id = ndb.StringProperty(indexed=False)
    client_secret = ndb.StringProperty(indexed=False)
    client_url = ndb.StringProperty(indexed=False)
    config_user = ndb.StringProperty(indexed=False)
    config_user_email = ndb.StringProperty(indexed=False)

    @classmethod
    def set_new(cls, client_id, client_secret, client_url, config_user, config_user_email ):
        info = ClientInfo( client_id=client_id, client_secret=client_secret, client_url=client_url, config_user=config_user, config_user_email=config_user_email, id='main' )
        info.put();

    @classmethod
    def get_latest(cls):
        return ndb.Key( ClientInfo, 'main' ).get()

class CredentialsInfo(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    credentials = ndb.PickleProperty(indexed=False)

    @classmethod
    def set_new(cls, credentials ):
        info = CredentialsInfo( credentials=credentials, id = 'main' )
        info.put()

    @classmethod
    def get_latest(cls):
        return ndb.Key(CredentialsInfo, 'main').get()

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
        import httplib2

        http = httplib2.Http()
        credentials.refresh( http );

TOKEN_ANCESTOR = ndb.Key( 'Gapier', 'Ancestor' )

class WorksheetToken(ndb.Model):
    created_date = ndb.DateTimeProperty(auto_now_add=True)
    alias = ndb.StringProperty(indexed=True)
    spreadsheet_key = ndb.StringProperty(indexed=False)
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

    def remove(self):
        self.key.delete()

    @classmethod
    def get_all(cls):
        return WorksheetToken.query(ancestor=TOKEN_ANCESTOR).fetch(999)

    @classmethod
    def add(cls, alias, listfeed_url, spreadsheet_key, password='', access_mode='full'):
        new = WorksheetToken( parent=TOKEN_ANCESTOR, id=alias, alias=alias, listfeed_url=listfeed_url, spreadsheet_key=spreadsheet_key, password=password, access_mode=access_mode )
        new.put()
        return new

    @classmethod
    def get_for_token(cls, token):
        import re
        parts = re.compile(r'\:').split( token )

        if len(parts) < 1:
            return False

        if len(parts) < 2:
            find_alias = parts[0]
            match_password=''
        else:
            find_alias = parts[0]
            match_password = parts[1]

        if not find_alias:
            return False

        found_object = ndb.Key(WorksheetToken, find_alias, parent=TOKEN_ANCESTOR).get()
        if not found_object:
            # legacy support for tokens without alias as id
            found_object = cls.query( cls.alias == find_alias, ancestor=TOKEN_ANCESTOR ).get()

        if not found_object:
            import logging
            logging.debug('alias not found')
            return False

        if found_object.password and not found_object.password == match_password:
            import logging
            logging.debug('password mismatch')
            return False

        return found_object

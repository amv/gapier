#!/usr/bin/env python

import sys
sys.path.append('vendor')

import webapp2
from gapier import handlers

app = webapp2.WSGIApplication([

    # Admin handlers

    ('/', handlers.MainHandler),
    ('/set_client', handlers.SetClientHandler),
    ('/start_connecting', handlers.StartConnectingHandler),
    ('/oauth2callback', handlers.OAuth2CallbackHandler),
    ('/list_tokens', handlers.ListTokensHandler),
    ('/get_document_list', handlers.GetDocumentListHandler),
    ('/get_document_sheet_list', handlers.GetDocumentSheetListHandler),
    ('/add_token', handlers.AddTokenHandler),
    ('/remove_token', handlers.RemoveTokenHandler),
    ('/add_bundle_sheet', handlers.AddBundleSheetHandler),
    ('/create_bundle', handlers.CreateBundleHandler),

    # User handlers

    ('/fetch', handlers.FetchHandler),
    ('/update_row', handlers.UpdateRowHandler),
    ('/add_row', handlers.AddRowHandler),
    ('/add_or_update_row', handlers.AddOrUpdateRowHandler),
    ('/remove_row', handlers.RemoveRowHandler),
    ('/trim_rows', handlers.TrimRowsHandler),

], debug=True)

gapier
======

HTTP server which gives you an API to add and update rows on Google spreadsheet documents easily

# Example

    npm install gapier
    
    // you can also use a fancier browser if you want..
    lynx -accept\_all\_cookies 'http://localhost:8091/setup'

    curl 'http://localhost:8091/set_row_value' \
        -d "sheet=GOOGLE_WORKSHEET_ID" \
        -d "column=diskusage" \
        --data-urlencode "row="$(hostname) \
        --data-urlencode "value="$(df|grep '/$'|sed -E 's/.* ([0-9]+%) .*/\1/')

# Why

Google spreadsheets is one of the most intuitive interfaces to interact with data from various sources. At least when you are already used to it.

There is Zapier to do this but at least for now it's row update functionality for google apps is missing completely. It also costs money and is not very flexible, error tolerant or verbose in problem situations.

# How

Gapier is a HTTP server which does the following things:

* it allows you to authenticate it to edit google spreadsheet documents for you
* then it exposes some HTTP POST endpoints which should make your life a bit easier

# Why not just a library

Unfortunately Google does not just allow you to edit stuff with your username and password.

Making updates to Google documents through code involves two layers of security:

* You need to create a OAuth2 client to identify your program which does the tasks
* You need to login in with your own account to authorize your OAuth2 client to make changes on your behalf

The first step leaves you with a OAuth2 client id and the second step leaves you with an OAuth2 refresh token.

In theory these two secrets are what allow you to go throught the many steps that result in a valid API call.

The practise however it involves ugly stuff like storing temporary access tokens across multiple program invocations. API access can also sometimes encounter odd things like expired tokens, rate limits on requests and even temporary server outages.

Some people (like me) find it a bit tedious to store these secrets and temporary state files in all the places where I happen to need the simple task of pushing some information to a Google spreadsheet.

The reason gapier was born was to package all that stuff in to a neat container.

# Security concerns

I would strongly advice you not to expose your service to the internet unless you are sure about some things:

1. You set up a password for gapier
2. You disabled gapier's network setup
3. The service can not be accessed without SSL (only using https://)
 
Gapier also stores your Google account access tokens on the disk as plaintext, so don't let other people read them.

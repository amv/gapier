gapier
======

Google App Engine deployable HTTP server which gives you an API to add, update and trim rows on Google spreadsheets easily.

PLEASE NOTE THAT THIS IS NOT YET DONE. THE DOCUMENTATION IS HERE JUST TO ACT AS A SPEC.

# Example usage

Once the server is running on GAE, it guides you on how to set it up. Just follow the instructions and set up a worksheet token for the following steps:

    lynx -accept_all_cookies 'http://localhost:8091/'

Once gapier is set up, this would look up the row which has the current machines hostname in it's "Hostname" column and update that rows "Disk usage" column.

    curl 'http://localhost:8091/update_row' \
        --data-urlencode 'worksheet_token=WORKSHEET_TOKEN' \
        --data-urlencode 'match_columns=Hostname'
        --data-urlencode 'match_values='$(hostname) \
        --data-urlencode 'set_columns=Disk usage' \
        --data-urlencode 'set_values='$(df|grep '/$'|sed -E 's/.* ([0-9]+%) .*/\1/')

This would look up a row using two columns and set two values. It would also add the row with both match and set values if it could not be found.

    curl 'http://localhost:8091/add_or_update_row' \
        --data-urlencode 'worksheet_token=WORKSHEET_TOKEN' \
        --data-urlencode 'match_columns=Hostname,Mount point'
        --data-urlencode 'match_values=testhost.github.com,/mnt/disk' \
        --data-urlencode 'set_columns=Disk usage, FS type' \
        --data-urlencode 'set_values=40%,ext4'

This does the same thing as the previous one but usin JSON is sometimes a bit easier to do from code.

    curl 'http://localhost:8091/add_or_update_row' \
        --data-urlencode 'worksheet_token=WORKSHEET_TOKEN' \
        --data-urlencode 'match_json={ "Hostname": "testhost", "Mount point": "/mnt/disk" }' \
        --data-urlencode 'set_json={ "Disk usage": "40%", "FS type": "ext4" }'

Sometimes you want to ensure that old or incorrect rows have not creeped in to your document. This makes sure only two rows exist.

    curl 'http://localhost:8091/trim_rows' \
        --data-urlencode 'worksheet_token=WORKSHEET_TOKEN' \
        --data-urlencode 'validate_columns=Hostname,Mount point'
        --data-urlencode 'validate_values=testhost,/mnt/disk' \
        --data-urlencode 'validate_values=testhost,/'

Naturally this can also be done using the JSON method.

    curl 'http://localhost:8091/trim_rows' \
        --data-urlencode 'worksheet_token=WORKSHEET_TOKEN' \
        --data-urlencode 'validate_json=[ { "Hostname": "testhost", "Mount point": "/mnt/disk" }, { "Hostname": "testhost", "Mount point": "/" } ]'

# Why

Google spreadsheets is one of the most intuitive interfaces to interact with data from various sources. But putting the data in automatically is usually a lot harder than you would like it to be.

There is Zapier to do this but at least for now it's row update functionality for google apps is missing completely. It also costs money and is not very flexible, error tolerant or verbose in problem situations.

Instead of acting as a simple proxy which sends each update to Google servers, gapier tries to ignore updates that would not lead to state changes and enforce unique key constraints in an environment where it is not natively supported. This allows the programmer to concentrate on more important things than cleaning up duplicate rows or tracking wether something has changed or not.

# Why not just a library

Google does not just allow you to put your username and password in function parameters and fire API calls on your behalf (the possibility is officially deprecated on April 20, 2012).

Making updates to Google spreadsheets with the suggested OAuth2 authorization involves two layers of security:

* You need to create a Google API project and an OAuth2 client to identify the programmer which is responsible for the API calls
* You then need to authorize your OAuth2 client to act on behalf of a user who has the rights to edit the wanted documents, which is done by sending the user to a specially crafted URL with their browser.

The first step leaves you with an OAuth2 client id and a secret. The second step leaves you with an OAuth2 refresh token.

In theory this ID, secret and token are what allow you to go throught the many steps that result in a valid API call.

The practise however involves ugly stuff like digging worksheet IDs through API calls and storing temporary access tokens across multiple program invocations. API access can also sometimes encounter odd things like expired tokens, rate limits on requests and even temporary server outages which are properly handled only by adding more state and delayed execution logic to your app.

The reason gapier was born was to put all this in to a neat GAE container which at least instructs you on how to proceed when it can not do things for you.

# How step 1: Register Client ID from Google

First register yourself a Google API project at https://code.google.com/apis/console/

After creating a project, you can find a great blue button under "API access" called "Create an OAuth 2.0 client ID". After pressing it, type a random name for your project name and press "Next". From the last configuration page choose the "Web application" and input "localhost" as hostname. Pressing "Create client ID" finishes what you need to do.

You have now created a Client ID! Congratulations! Now take note of the "Client ID" and "Client secret" lines on the newly created Client ID box as they are something you need to input to gapier after installation.

# How step 2: Install gapier

TODO

# Security concerns

I would strongly advice you not to expose your service to the internet unless you are sure about some things:

1. You set up a password for gapier
2. You disabled gapier's network setup
3. The service can not be accessed without SSL (only using https://)
 
Gapier also stores your Google account access tokens on the disk as plaintext, so don't let other people read them.

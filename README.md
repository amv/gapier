gapier
======

HTTP server which gives you an API to add and update rows on Google spreadsheet documents easily.

PLEASE NOTE THAT THIS IS NOT YET DONE. THE DOCUMENTATION IS HERE JUST TO ACT AS A SPEC.

# Example

Install gapier to your local machine:

    npm install gapier
    
Once the server is running, it needs to be set up. Follow the instructions on the setup page. You can also use a fancier browser if you wish :)
    
    lynx -accept_all_cookies 'http://localhost:8091/setup'

Once gapier is set up, this would look up the row which has the current machines hostname in it's "Hostname" column and update that rows "Disk usage" column.

    curl 'http://localhost:8091/update_row' \
        --data-urlencode 'sheet=GOOGLE_WORKSHEET_ID' \
        --data-urlencode 'match_columns=Hostname'
        --data-urlencode 'match_values='$(hostname) \
        --data-urlencode 'set_columns=Disk usage' \
        --data-urlencode 'set_values='$(df|grep '/$'|sed -E 's/.* ([0-9]+%) .*/\1/')

This would look up a row using two columns and set two values. It would also add the row if it could not be found.

    curl 'http://localhost:8091/add_or_update_row' \
        --data-urlencode 'sheet=GOOGLE_WORKSHEET_ID' \
        --data-urlencode 'match_columns=Hostname,Mount point'
        --data-urlencode 'match_values=testhost.github.com,/mnt/disk' \
        --data-urlencode 'set_columns=Disk usage, FS type' \
        --data-urlencode 'set_values=40%,ext4'

This does the same thing as the previous one but usin JSON is sometimes a bit easier to do from code.

    curl 'http://localhost:8091/add_or_update_row' \
        --data-urlencode 'sheet=GOOGLE_WORKSHEET_ID' \
        --data-urlencode 'match_json={ "Hostname": "testhost", "Mount point": "/mnt/disk" }' \
        --data-urlencode 'set_json={ "Disk usage": "40%", "FS type": "ext4" }'

Sometimes you want to ensure that old or incorrect rows have not creeped in to your document. This makes sure only two rows exist.

    curl 'http://localhost:8091/strip_rows_to' \
        --data-urlencode 'sheet=GOOGLE_WORKSHEET_ID' \
        --data-urlencode 'validate_columns=Hostname,Mount point'
        --data-urlencode 'validate_values=testhost,/mnt/disk' \
        --data-urlencode 'validate_values=testhost,/'

Naturally this can also be done using the JSON method.

    curl 'http://localhost:8091/strip_rows_to' \
        --data-urlencode 'sheet=GOOGLE_WORKSHEET_ID' \
        --data-urlencode 'validate_json=[ { "Hostname": "testhost", "Mount point": "/mnt/disk" }, { "Hostname": "testhost", "Mount point": "/" } ]'

# Why

Google spreadsheets is one of the most intuitive interfaces to interact with data from various sources. But putting the data in automatically is usually a lot harder than you would like it to be.

There is Zapier to do this but at least for now it's row update functionality for google apps is missing completely. It also costs money and is not very flexible, error tolerant or verbose in problem situations.

Instead of acting as a simple proxy which sends each update to Google servers, gapier tries to ignore updates that would not lead to state changes and enforce unique key constraints in an environment where it is not natively supported. This allows the programmer to concentrate on more important things than cleaning up duplicate rows or tracking wether something has changed or not.

# Why not just a library

Unfortunately Google does not just allow you to edit stuff with your username and password.

Making updates to Google documents through code involves two layers of security:

* You need to create an API project and an OAuth2 client to identify your program which is responsible for the API calls
* You need to login in with your own account to authorize your OAuth2 client to make changes on your behalf

The first step leaves you with a OAuth2 client id and a secret. The second step leaves you with an OAuth2 refresh token.

In theory this ID and these two secrets are what allow you to go throught the many steps that result in a valid API call.

The practise however it involves ugly stuff like storing temporary access tokens across multiple program invocations. API access can also sometimes encounter odd things like expired tokens, rate limits on requests and even temporary server outages.

Some people (like me) find it a bit tedious to store these secrets and temporary state files in all the places where I happen to need the simple task of pushing some information to a Google spreadsheet.

The reason gapier was born was to put all that stuff in to a neat container.

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

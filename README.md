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

There is Zapier to do this but at least for now it's row update functionality for Google spreadsheets is missing completely. It also costs money and is not very flexible, error tolerant or verbose in problem situations.

Instead of acting as a simple proxy which sends each update to Google servers, gapier tries to ignore updates that would not lead to state changes and enforce unique key constraints in an environment where it is not natively supported. This allows the programmer to concentrate on more important things than cleaning up duplicate rows or tracking wether something has changed or not.

# Why not just a library

Google does not just allow you to put your username and password in function parameters and fire API calls on your behalf (the possibility is officially deprecated on April 20, 2012). And even if it did, you usually do not want to have your full account credentials stored as plain text in files.

Making updates to Google spreadsheets with the suggested OAuth2 authorization involves two layers of security:

* You need to create a Google API project and an OAuth2 client to identify the programmer which is responsible for the API calls
* You then need to authorize your OAuth2 client to act on behalf of a user who has the rights to edit the wanted documents, which is done by sending the user to a specially crafted URL with their browser.

The first step leaves you with an OAuth2 client id and a secret. The second step leaves you with an OAuth2 refresh token.

In theory this ID, secret and token are what allow you to go throught the many steps that result in a valid API call - and these you could store in your deployments.

The practise of getting this information however involves ugly stuff like digging worksheet IDs through handcrafted API calls and storing temporary access tokens across multiple program invocations. API access can also sometimes encounter odd things like expired tokens, rate limits on requests and even temporary server outages which are properly handled only by adding more state and delayed execution logic to your app.

The reason gapier was born was to put all this in to a neat GAE container, which at least instructs you on how to proceed when it can not do things for you. Gapier also gives you spreadsheet specific tokens to store in your deployments instead of having to store credentials that allow accessing all of your spreadsheets.


# How step 1: Install gapier

1. TOOD: checkout gapier from github
2. TODO: import project to GAE
3. TODO: start gapier from GAE launcher on port 8091 (to stay consistent with these docs)
4. TODO: optionally publish project on appspot.com, just remember to change localhosts to your appspot url

# How step 2: Register a new Google API project

1. TODO: create a project at https://code.google.com/apis/console/
2. TODO: under "API access" press "Create an OAuth 2.0 client ID"
3. TODO: type a random name for your project name and press "Next"
4. TODO: choose the "Web application" and input "localhost" as hostname
5. TODO: press "Create client ID" and take note of the "Client ID" and "Client secret" lines on the newly created Client ID box

# How step 3: Configure gapier yo use your Google API project

1. TODO: open browser at http://localhost:8091/
2. TODO: input Client ID and Client secret to prompts
3. TODO: make sure the url base matches your browser location so that authentication finds back

# How step 4: Link gapier with your Google account

1. TODO: open browser at http://localhost:8091/
2. TODO: Press "connect with google"
3. TODO: Grant your API project the rights to modify your spreadsheets
4. TODO: Gapier is now tied to your account. Only you can edit the worksheet tokens and spreadsheet changes will be done as "you".
5. TODO: if you ever want to change this, you need to remove some objects from GAE data store by hand

# How step 5: Create a worksheet token for an existing Google spreadsheet

1. TODO: open browser at http://localhost:8091/
2. TODO: click "add worksheet token"
3. TODO: open the target spreadsheet in an another window and copy&paste the document key from the location bar as instructed
4. TODO: pick the sheet from the spreadsheet which you want to edit with this token
5. TODO: input an unique worksheet alias which will act as the base of your worksheet token
6. TODO: copy the alias:randomchars token to your code to authorize gapier API calls for this sheet

# Security concerns

I would strongly advice you not to expose your service to the internet unless you are using it through SSL (https:// only).
 
Gapier also stores your API project secrets, Google account access tokens and worksheet token passwords in the data store as cleartext for your convenience so don't expose any passwords that you are afraid to lose.

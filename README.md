Gapier
======

Add, update, trim and fetch Google Spreadsheet rows with a limited but easy to use HTTP API that can be deployed to Google App Engine.

PLEASE NOTE THAT THIS IS ALPHA QUALITY:

 * Most of the views are coder graphics.
 * The install process does not guide you clearly.
 * Most of the error situations are unhandled.
 * There are no automated test.

This will hopefully get better over time. At this stage all suggestions on code quality are more than welcome as this is my first real Pyhon project, my first real Google App Engine project and my first real Angular JS project at the same time.

# Quick examples

**IMPORTANT NOTE**: The first empty row in a worksheet ends sheet. This is a Google Spreadsheets listfeed feature. So **IF YOU CAN ACCESS ONLY THE BEGINNING OF THE LIST**, make sure you have no empty rows in your worksheet.

Fetch worksheet rows as a JSON list:

    curl 'https://mygapier.appspot.com/fetch?worksheet_token=your:token'

Add a row to your worksheet with JSON:

    curl 'https://mygapier.appspot.com/add_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'set_json={"Hostname":"my-machine","Disk usage":"12%"}'
        
Do the same with HTTP param interface:

    curl 'https://mygapier.appspot.com/add_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'set_columns=Hostname,Disk usage' \
        --data-urlencode 'set_values=my-machine,12%'

Update the existing "my-machine" row. Add the row if it does not exist:

    curl 'https://mygapier.appspot.com/add_or_update_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'match_json={ "Hostname":"my-machine" }' \
        --data-urlencode 'set_json={ "Disk usage":"52%" }'

.. and the same update with HTTP param interface:

    curl 'https://mygapier.appspot.com/add_or_update_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'match_columns=Hostname' \
        --data-urlencode 'match_values=my-machine' \
        --data-urlencode 'set_columns=Disk usage' \
        --data-urlencode 'set_values=52%'

Make sure that only "machine-1" and "machine-2" for user "Me" are the only two rows on the spreadsheet:

    curl 'https://mygapier.appspot.com/trim_rows' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'validate_json=[{ "Hostname":"machine-1","User":"Me" }, { "Hostname":"machine-2","User":"Me" }]'
        
.. and with HTTP params:

    curl 'https://mygapier.appspot.com/trim_rows' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'validate_columns=Hostname,User' \
        --data-urlencode 'validate_values=machine-1,Me' \
        --data-urlencode 'validate_values=machine-2,Me'

# General concepts

    TODO: deploying to GAE with expected costs
    TODO: creating a worsheet token for code deployments
    TODO: choosing between JSON and HTTP param interfaces
    TODO: tips on using entry sheets with formula & chart sheets

# Available actions

## /fetch

Fetches all spreadsheet rows as a list of JSON objects.

The first row defines the object keys and the following rows each show as a separate object.

Accepts worksheet\_token both as GET and POST parameters. 

## /add\_or\_update\_row

Looks up the rows that match the "match" definition. Updates the columns on those rows to match the "set" definition.

If no rows match the "match" definition, inserts a new row with data from both the "match" and the "set" definitions.

Accepts only POST requests. Boths "match" and "set" definitions can be given using either the \_json notation or combining a \_columns and a \_values notation.

## /add\_row

Inserts a new row with data from both the "match" and the "set" definitions unless a row matching the "match" definition already exists.

Either the "match" or the "set" sefinition can be left out. If only the "set" definition is specified, might result in a spreadsheet with multiple rows of the same data.

Accepts only POST requests. Boths "match" and "set" definitions can be given using either the \_json notation or combining a \_columns and a \_values notation.

## /update\_row

Looks up the rows that match the "match" definition. Updates the columns on those rows to match the "set" definition.

Returns 404 if no matching rows were found.

Accepts only POST requests. Boths "match" and "set" definitions can be given using either the \_json notation or combining a \_columns and a \_values notation.

## /delete\_row

Looks up the rows that match the "match" definition. Removes those rows.

Returns 404 if no matching rows were found.

Accepts only POST requests. The "match" definition can be given using either the \_json notation or combining a \_columns and a \_values notation.

## /trim\_rows

Goes through each row of the worksheet. Removes all rows that are not present in the "validate" definition list.

Accepts only POST requests. The "validate" definition can be given using either the \_json notation or combining one \_columns and multiple \_values notations.

# Why

Google spreadsheets is one of the most intuitive interfaces to interact with data from various sources. However putting the data in automatically is usually a lot harder than you would like it to be.

This project is inspired by Zapier and tries to expand it's limited feature set when dealing with Google Spreadsheets.

Instead of acting as a simple proxy which sends each update to Google servers, gapier tries to ignore updates that would not lead to state changes and enforce unique key constraints in an environment where it is not natively supported. This allows the programmer to concentrate on more important things than caching data, cleaning up duplicate rows or tracking wether something has changed or not.

Gapier tries to help with challenges with managing sensitive secrets in code deployments.

## Why not just a library

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

Gapier
======

Gapier gives you a simple HTTP API to modify Google Spreadsheets, with simple tokens as authentication.

One Google Account acts as the admin of the service and can create any number of limited access tokens for different spreadsheets that the user can access.

Built to be deployed to Google App Engine Standard and to incur no costs for a vast majority of use cases.

- [Quick examples](#quick-examples)
- [Limitations and common pitfalls](#limitations-and-common-pitfalls)
- [How can I use Gapier?](#how-can-i-use-gapier)
- [How can I use formulas in my Gapier spreadsheets?](#how-can-i-use-formulas-in-my-gapier-spreadsheets)
- [How to use Gapier safely directly from a public web page?](#how-to-use-gapier-safely-directly-from-a-public-web-page)
- [Reference of the available HTTP actions](#reference-of-the-available-http-actions)
  - [/fetch](#fetch)
  - [/add\_or\_update\_row](#add_or_update_row)
  - [/add\_row](#add_row)
  - [/update\_row](#update_row)
  - [/delete\_row](#delete_row)
  - [/trim\_rows](#trim_rows)
- [Why does Gapier exist?](#why-does-gapier-exist)
  - [Why a service and not just a library?](#why-a-service-and-not-just-a-library)
- [Installation](#installation)
  - [Register and configure a new Google project](#register-and-configure-a-new-google-project)
  - [Create an App Engine service in the project](#create-an-app-engine-service-in-the-project)
  - [Configure your Gapier service](#configure-your-gapier-service)

# Quick examples

Fetch worksheet rows as a JSON list of objects:

    curl 'https://mygapier.appspot.com/fetch?worksheet_token=your:token'

Add a row to your worksheet with JSON:

    curl 'https://mygapier.appspot.com/add_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'set_json={"Hostname":"my-machine","Disk usage":"12%"}'

Add the same row, using the HTTP param interface:

    curl 'https://mygapier.appspot.com/add_row' \
        --data-urlencode 'worksheet_token=your:token' \
        --data-urlencode 'set_columns=Hostname,Disk usage' \
        --data-urlencode 'set_values=my-machine,12%'

Add the same row from a web page using JQuery and the JSONP transport (uses HTTP params, but JSON can be used too):

    $.ajax({
        url: 'https://mygapier.appspot.com/add_row',
        callback: '?',
        dataType: 'jsonp',
        data: {
            worksheet_token: 'your:token',
            set_columns: 'Hostname,Disk usage',
            set_values: 'my-machine,12%'
        }
    });

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

# Limitations and common pitfalls

 1. **NO FORMULAS** can be read or written because Gapier uses the Listfeed API. However, [you can work around this easily](#how-can-i-use-formulas-in-my-gapier-spreadsheets).
 2. **NO EMPTY ROWS** because rows after the first one are not visible to Gapier. This too is a Listfeed API "feature".
 3. No tests yet, so there are probably bugs :(

# How can I use Gapier?

One of the design goals of Gapier is that you do NOT need to have your own servers or pay maintenance fees for someone hosting Gapier for you on their servers.

That being said, you do need to have your own version of the Gapier service installed "somewhere" for you to use it. The intended "somewhere" is to use the Google Cloud free tier infrastructure (App Engine) to run Gapier for you. The "Installation" -section at the end of this document offers an easy to follow step by step guide for achieving just this.

# How can I use formulas in my Gapier spreadsheets?

Model your spreadsheet so that they have separate sheets for dynamic data and separate sheets for formulas. Then you use Gapier to update your dynamic sheets, import the data from one or several dynamic sheets to certain formula sheet columns, and create your formulas by hand in other columns.

You have several options to copy your dynamic sheet data to your formula sheets, but here are the most common ones:

    ={'Sheet1'!A:A}
    ={'Sheet1'!A:C}

    =FILTER('Sheet1'!A:A,{TRUE})
    =FILTER('Sheet1'!A:C,{TRUE,TRUE,TRUE})

    =QUERY(Sheet1!A:A,"select A")
    =QUERY(Sheet1!A:C,"select A,B,C")

You should look at the documentation of `=FILTER` and `=QUERY` if you want to visualize or process only parts of your dynamic data.

# How to use Gapier safely directly from a public web page?

Gapier ships with a JSONP transport, which means that any web page which has the access token can interact with the token's spreadsheet through Gapier.

Using a token with full read & write access to a spreadsheet from a public website is however often not something you want to do. What you usually would want to do instead is one of the following:

 * Use a **read-only token** to display data on your website that is authored manually through the spreadsheet.
 * Use a **add-only token** to allow users to submit a form and add the form data to a new row in the spreadsheet for later processing.
 * Combine the multiple instances of the two above with some magic formula for processing :)
 * Just use a **full access token** if your website is an otherwise protected internal tool or a prototype with friendly users.

Currently Gapier does not yet allow limiting the "origin" of the requests, so that access would be possible only from websites on specified domains, but this is a planned future feature.

# Reference of the available HTTP actions

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

# Why does Gapier exist?

Spreadsheets (Google or otherwise) are one of the most intuitive and flexible interfaces to interact with data from various sources. However putting the data in spreadsheets automatically is usually a lot harder than one would like it to be.

Gapier exists to make this process as easy as possible from any source that can send simple HTTP requests.

To achieve this goal, Gapier does 2 main things:

 * Gapier manages your sensitive secrets and **gives you simple tokens with limited access rights** that you can safely deploy to servers or websites.
 * Gapier exposes a simple HTTP API that **allows easily adding and updating rows** without doing row matching yourself.

This project was originally inspired by Zapier and tried to expand it's limited feature set when dealing with Google Spreadsheets. If you are a fan of Zapier, you will find that Gapier should be easy to use through the custom code steps with the `request` library.

## Why a service and not just a library?

The service approach yields benefits for security, latency and ease of deployment.

Security: A service which holds a small amount of state can greatly ease the management of the various OAuth2 secrets that are involved in modifying a Google spreadsheet. By storing these delicate secrets in the same domain as the spreadsheets themselves (in the Google infrastructure), and giving out only very limited access tokens, many attack vectors are simply eliminated, and incident surfaces diminished greatly.

Latency: Many convenient update operations on a spreadsheet require accessing and processing the whole spreadsheet. When this is done in the Google infrastructure instead of transporting the data to the "edges" for libraries to process, processing latencies can be greatly reduced. Latencies also apply to token renewals, which can be either eliminated by mostly reusing tokens cached across clients, or diminished by locality within the Google infrastructure.

Ease of deployment: Exposing the service through HTTP allows deploying spreadsheets altering logic to very limited environments, like software macros or embedded function as a service tools. Also the amount of deployed configuration needed to access the service with a single token is much smaller and simpler than what would be needed to properly configure a library which uses OAuth2.

While Gapier does not yet support it, it would also be possible to extend the service approach to add deferred logic to handle situations like rate limiting errors and intermittent partial service outages. But even without these features in place, the service approach allows maintainers better visibility to the potential problems in the system through the Google App Engine logs, independent of the capabilities offered by the edge clients that would use libraries.

# Installation

## Register and configure a new Google project

1. You probably need a Google Account :)
2. Create a project at https://console.developers.google.com/cloud-resource-manager
3. Pick an unique name like "myorg-myname-gapier" and take note of the project ID from the gray "Your project ID will be myorg-myname-gapier" text that appears.
4. Select your new project and then pick "API Manager" from the console main menu.
5. Enter the "Library" section, search for the API called "Google Calendar API" and "Enable" it.
6. Enter the "Credentials" section enter the "OAuth2 consent screen" area.
7. Set a fancy name (like "Gapier") as the "Product name" and save your settings.
8. Enter the "Credentials" area and create "OAuth client ID" credentials.
9. Pick "Web application" type and fill in the "Authorized redirect URIs" field with. "https://myorg-myname-gapier.appspot.com/oauth2callback".
10. Make sure the first part of the domain matches your project ID from step 3 and click "Create".
11. Copy and store both the Client ID and the Client secret for the credentials you just created.

## Create an App Engine service in the project

1. Select "GOOGLE CLOUD PLATFORM" from the bottom of the console main menu.
2. Pick "App Engine" From the cloud console main menu.
3. Create "Your first app" by choosing "Python" as your language.
4. Select the region closest to you, click "Next" and wait for the initialization to complete.
5. Follow a few steps of the tutorial until you get a black cloud console at the bottom of your browser.
6. Click "Cancel Tutorial" and input the following commands to your cloud console:

Note that you need to answer (y) to the last two commands.

    git clone https://github.com/amv/gapier ~/gapier
    cd gapier
    gcloud datastore create-indexes index.yaml
    gcloud app deploy app.yaml

## Configure your Gapier service

1. First open your browser at "https://myorg-myname-gapier.appspot.com/". If you see an error, please wait for a while for the index to be created and reload the page.
2. Click "Log in!". Gapier administration will be permanently bound to the first user who logs in, and no other users can manage the tokens.
2. Gapier should now ask you for the Client ID and Client secret of the API Credentials you created earlier. The domain should be pre-filled correctly.
3. After storing the credentials, Gapier will guide you to allow it to access to spreadsheets on behalf of some user.
4. After granting access to spreadsheets, you should be able to start adding spreadsheet tokens!

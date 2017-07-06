BitStore is a DataHub microservice for storing blobs i.e. files. It is a lightweight auth wrapper for an S3-compatible object store that integrates with the rest of the DataHub stack and especially the `auth` service.

[![Build Status](https://travis-ci.org/datahq/bitstore.svg?branch=master)](https://travis-ci.org/datahq/bitstore)

## Quick Start

* Clone the repo,
* install dependencies from requirements.txt,
* and run the server (server.py)

## Env Vars

* `SERVICE_NAME` - the name of this microservice. Used for permission checking in auth and for url mountpoint of application
  * default = rawstore
* `DATAHUB_PUBLIC_KEY` - the public key for communicating with the auth server. Get this from the auth server setup.
* Config for the underlying objectstore service (boto compatible)
* `BASE_PATH` - base path for upload URL on s3. May contain any format string available for a file in authorize API including {path} which is full path string (relative path to file in package)
  * Example: `custom/path/{owner}/{name}/{path}` will end up with `custom/path/datahq/datax/data/file.csv` 

  ```
  STORAGE_ACCESS_KEY_ID
  STORAGE_SECRET_ACCESS_KEY
  STORAGE_HOSTNAME
  STORAGE_BUCKET_NAME
  ```

Note: requested permissions to auth server will be like:

```
permissions:
  datapackage-upload
service:
  SERVICE_NAME (config defined above e.g. 'rawstore')
```


## API

### Get authorized upload URL(s)

`/authorize`

**Method:** `POST`

**Query Parameters:**

 - `jwt` - permission token (received from `/user/authorize`)

**Headers:**

 - `Auth-Token` - permission token (can be used instead of the `jwt` query parameter)

**Body:**

JSON content with the following structure:

```json
{
    "metadata": {
        "owner": "<user-id-of-uploader>",
        "name": "<data-set-unique-id>"
    },
    "filedata": {
        "<relative-path-to-file-in-package-1>": {
            "length": 1234, #length in bytes of data
            "md5": "<md5-hash-of-the-data>",
            "type": "<content-type-of-the-data>",
            "name": "<file-name>"
        },
        "<relative-path-to-file-in-package-2>": {
            "length": 4321,
            "md5": "<md5-hash-of-the-data>",
            "type": "<content-type-of-the-data>",
            "name": "<file-name>"
        }
        ...
    }
}
```

`owner` must match the `userid` that is in the authentication token.

**Returns**

Signed urls to upload into S3:

```javascript=
{
  fileData: {
    "<file-name-1>": {
      "md5-hash": "...",
      "name": "<file-name>",
      "type": "<file-type>",
      "upload_query": {
        'Content-MD5': '...',
        'Content-Type': '...',
        'acl': 'public-read',
        'key': '<path>',
        'policy': '...',
        'x-amz-algorithm': 'AWS4-HMAC-SHA256',
        'x-amz-credential': '...',
        'x-amz-date': '<date-time-in-ISO',
        'x-amz-signature': '...'
      },
      "upload_url": "<s3-url>"
    },
    "<file-name-2>": ...,
    ...
  }
}
```

### Get information regarding the datastore

`/info`

**Method:** `GET`

**Query Parameters:**

 - `jwt` - permission token (received from `/user/authorize`)

**Headers:**

 - `Auth-Token` - permission token (can be used instead of the `jwt` query parameter)

**Returns:**

JSON content with the following structure:
```json
{
    "prefixes": [
        'https://datastore.openspending.org/123456789',
        ...
    ]
}
```

`prefixes` is the list of possible prefixes for an uploaded file for this user.

TO TEST
=======

*   ~~Output is consistently updated, especially from one round to the next. The `local_db[<key>]` calls should hit a cache one the doc with that key exists in the cache. Is the cache updated as the docs change or are we getting stale data? Use HTTP requests to CouchDB if we get stale data.~~
    *   Tested. The cloudant cache seems to be invalidated or updated as docs change in the db.
*   What happens if the network connection is lost and regained? Do the clients automatically reconnect? Does iteration through the changes feed continue? Or do we have to re-establish all that?

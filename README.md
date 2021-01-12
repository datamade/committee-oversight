# committee-oversight
⚖️ Committee oversight map coding project for the Lugar Center

## Requirements

- [Docker](https://www.docker.com/)


## Running the app locally

We use Docker for local development. To get started, run the following from your terminal:

1. Clone this repository and `cd` into your local copy.

    ```bash
    git clone git@github.com:datamade/committee-oversight.git
    cd committee-oversight
    ```

2. DataMade employees can download the most recent copy of the scraped committee hearings `hearings.dump` from `datamade-postgresql-backups/hearings` bucket in S3. Otherwise you'll need to run [the hearings scraper]( https://github.com/datamade/hearings/) to populate your application database with the latest committee hearings. **Subsequent steps will not work until you add initial hearings data to your database.**

3. If you ran the hearings scraper in Step 2, you can skip this step. To load `hearings.dump` into your database, run:

    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.db-ops.yml run -e PGPASSWORD=postgres --rm dbload-dump
    ```

4. Run migrations and load in various fixtures:

    ```bash
    docker-compose -f docker-compose.yml -f docker-compose.db-ops.yml run --rm dbload-fixtures
    ```

5. Run the application:

    ```bash
    docker-compose up
    ```

6. You should be able to log in with the DataMade `testuser`. If you don't have those credentials,
create a new superuser:

    ```bash
    docker-compose run --rm app python manage.py createsuperuser
    ```

7. Navigate to http://localhost:8000/ to view the site!

## Testing

To run the tests:

```bash
docker-compose -f docker-compose.yml -f tests/docker-compose.yml run --rm app
```


## Initial CMS content

The `dbload-fixtures` command in step 3 above will load initial CMS data. If you'd like to do it separately, run:

```bash
docker-compose run --rm app python manage.py load_cms_content
```

**To create a new dump** of all the content in the Wagtail backend, perform the following steps:

1. Back up the CMS content (except for image files) with the following 2 commands:

    ```bash
    docker-compose run --rm app python manage.py dumpdata --natural-foreign --indent 2 \
        -e core \
        -e legislative \
        -e committeeoversightapp \
        -e contenttypes \
        -e auth.permission \
        -e wagtailcore.groupcollectionpermission \
        -e wagtailcore.grouppagepermission \
        -e wagtailimages.rendition \
        -e sessions > committeeoversightapp/fixtures/initial_cms_content.json
    ```

    ```bash
    docker-compose run --rm app python manage.py dumpdata --natural-foreign --indent 2 \
        committeeoversightapp.landingpage \
        committeeoversightapp.staticpage \
        committeeoversightapp.categorydetailpage \
        committeeoversightapp.committeedetailpage \
        committeeoversightapp.hearinglistpage \
        committeeoversightapp.comparecurrentcommitteespage \
        committeeoversightapp.comparecommitteesovercongressespage \
        > committeeoversightapp/fixtures/initial_cms_content_custom_pages.json
    ```

    This should update the `initial_cms_content.json` file in your `committeeoversightapp/fixtures`
    directory.

2. Update the image files by copying your local Wagtail images folder into `fixtures/initial_images`:

    ```bash
    cp -R media/original_images/. committeeoversightapp/fixtures/initial_images/
    ```

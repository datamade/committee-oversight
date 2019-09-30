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

2. Run the application:

    ```bash
    docker-compose up
    ```

3. The root of this repository has a file named `hearings.dump`, a sample set of hearings data for use in local development. With `docker-compose up` still running, open a new terminal tab and run:

    ```bash
    docker-compose exec postgres pg_restore -C -j4 --no-owner -U postgres -d hearings /app/hearings.dump
    docker-compose exec app python manage.py migrate
    ```

    Note: To accommodate the restoration of this hearings dump, migrations are not run automatically with `docker-compose up`. If you need to run them manually, you can run `docker-compose run --rm app python manage.py migrate`.

4. If you don't already have the `lugarcenter` development password, create a new superuser by running:

    ```bash
    docker-compose run --rm app python manage.py createsuperuser
    ```

5. Navigate to http://localhost:8000/ and you should be able to log in!


## Initial CMS content

**To restore an existing backup of the Wagtail CMS**, run:

```bash
docker-compose run --rm app python manage.py load_cms_content
```

**To create a new dump** of all the content in the Wagtail backend, perform the following steps:

1. Back up the CMS content (except for image files):

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

    docker-compose run --rm app python manage.py dumpdata --natural-foreign --indent 2 \
        committeeoversightapp.landingpage \
        committeeoversightapp.staticpage \
        committeeoversightapp.categorydetailpage \
        committeeoversightapp.committeedetailpage > committeeoversightapp/fixtures/initial_cms_content_custom_pages.json
    ```

    This should update the `initial_cms_content.json` file in your `committeeoversightapp/fixtures`
    directory.

2. Update the image files by copying your local Wagtail images folder into `fixtures/initial_images`:

    ```bash
    cp -R media/original_images/. committeeoversightapp/fixtures/initial_images/
    ```

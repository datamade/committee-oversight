# committee-oversight
⚖️ Committee oversight map coding project for the Lugar Center

## Requirements

- Python 3.x
- Postgres >= 9

## Running the app locally

Perform the following steps from your terminal.

1. Clone this repository and `cd` into your local copy.

    ```bash
    git clone git@github.com:datamade/committee-oversight.git
    cd committee-oversight
    ```
2. Create a virtual environment. (We recommend using [`virtualenvwrapper`](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) for working in a virtualized development environment.)

    ```bash
    mkvirtualenv committee-oversight
    ```
3. Install the requirements.

    ```bash
    pip install -r requirements.txt
    ```

4. Copy the example local settings file to the correct location:

    ```bash
    cp committeeoversight/local_settings.example.py committeeoversight/local_settings.py
    ```

5. Start a `hearings` database with a scrape from the [hearings repo](https://github.com/datamade/hearings) or a data dump from a pal. If you're following the latter path and have an archival format `hearings.dump` file (see [documentation](https://www.postgresql.org/docs/10/app-pgrestore.html)) in the root of this project, restore it by running:

    ```bash
    pg_restore -C -j4 --no-owner hearings.dump | psql
    ```

6. Run migrations:

    ```bash
    python manage.py migrate
    ```

7. Make a superuser for so that you can access the admin interface:

    ```bash
     python manage.py createsuperuser
    ```

    Django should prompt you to provide a username, email, and password.

8. Load hearing categories:

    ```bash
    python manage.py loaddata hearingcategorytype
    ```

9. Run the app locally!

    ```bash
    python manage.py runserver
    ```

    Then, navigate to http://localhost:8000/.

## Initial CMS content

*To create a new data dump* of all the content in the Wagtail backend—except for
image files—run:

```bash
python manage.py dumpdata --natural-foreign --indent 2 -e core -e legislative -e committeeoversightapp -e contenttypes -e auth.permission -e wagtailcore.groupcollectionpermission -e wagtailcore.grouppagepermission -e wagtailimages.rendition -e sessions > committeeoversightapp/fixtures/initial_cms_content.json
```

This should update the `initial_cms_content.json` file in your `committeeoversightapp/fixtures`
directory.

To update the images, find your `media` folder and copy the contents of `original_images`
into `committeeoversightapp/fixtures/initial_images`. For local development:

```bash
cp -R media/original_images/. committeeoversightapp/fixtures/initial_images/
```

*To restore an existing CMS data dump*, run:

```bash
python manage.py load_cms_content
```

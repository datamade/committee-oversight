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

5. Start a `hearings` database with a partial scrape from the [hearings repo](https://github.com/datamade/hearings) or a data dump from a pal.

6. Run migrations:

    ```bash
    python manage.py migrate
    ```

7. Make a superuser for so that you can access the admin interface:

    ```bash
     python manage.py createsuperuser
    ```

    Django should prompt you to provide a username, email, and password.

8. Run the app locally!

    ```bash
    python manage.py runserver
    ```

    Then, navigate to http://localhost:8000/.

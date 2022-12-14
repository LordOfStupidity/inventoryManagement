from os import environ, listdir
from re import compile, IGNORECASE

from bcrypt import gensalt, hashpw, checkpw
from phonenumbers import is_valid_number, parse
from requests import post
from sqlalchemy import insert, select, update, delete, func, distinct, cast, Integer

from app.database.DatabaseTables import Account, PartStore, Job, Part, PartType
from app.decorators.flask_decorators import db_connector


# Prevent inputs that only contain spaces from being entered into the database
def check_input(test_input: str) -> bool:
    if test_input and not test_input.isspace() and '-' not in test_input:
        return True
    return False


# Create MD5 hash of password to insert into database
def create_password_hash(password: bytes) -> bytes:
    salt = gensalt()
    hashed = hashpw(password, salt)
    if check_password_hash(password, hashed):
        return hashed


# Check if the password is equal to each other
def check_password(password: str, conf_password: str) -> bool:
    if password == conf_password:
        return True
    return False


# Check if MD5 hash matches the password given
def check_password_hash(password: bytes, my_hash: bytes) -> bool:
    if checkpw(password, my_hash):
        return True
    return False


# Get difference of two values
def get_difference(op1: int, op2: int) -> int:
    if op1 > op2 or op1 == op2:
        return op1 - op2
    elif op1 < op2:
        return op2 - op1


# Check that the phone number is valid using the phonenumbers package
def check_phone_num(phone_num: str) -> bool:
    pattern = compile(r'^[\dA-Z]{3}[\dA-Z]{3}[\dA-Z]{4}$', IGNORECASE)

    # Use the phonenumbers package to make sure the phonenumber is valid
    check_number = parse('+1' + phone_num, 'US')
    valid_number = is_valid_number(check_number)

    if pattern.match(phone_num) is not None and valid_number:
        return True
    return False


# Get the part store icon file names in the /assets/stores/ directory
def get_store_icon_names() -> list:
    items = listdir('app/static/assets/stores')
    return [i.rstrip('.svg') for i in items]


# Check if icon file exists
def check_if_icon_exists(icon: str) -> bool:
    items = get_store_icon_names()

    if icon in items:
        return True
    return False


@db_connector
def get_current_store_name_icon(part_store_id: str, **kwargs) -> list:
    connection = kwargs.pop('connection')
    stmt = (select(PartStore.part_store_name, PartStore.icon).where(
        PartStore.id == part_store_id))
    results = connection.execute(stmt).fetchall()
    return [i for i in results][0]


class DatabaseManipulator:
    # Get all parts entries from database
    @db_connector
    def fetchall(self, **kwargs) -> tuple:
        conn = kwargs.pop('connection')
        stmt = conn.query(Part.id, Part.name, Part.amount,
                          Part.part_number, Part.part_store_name, Part.type, Part.unit)
        results = conn.execute(stmt).fetchall()
        return results

    # Get part type names
    @db_connector
    def get_part_type_names(self, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(PartType.type_name))
        results = connection.execute(stmt).fetchall()
        res = [i[0] for i in results]
        return res

    # Get all phone numbers/users
    @db_connector
    def get_phone_numbers(self, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(Account.username).where(Account.is_confirmed == 1))
        results = connection.execute(stmt).fetchall()
        return results

    # Get all part types
    @db_connector
    def get_part_types(self, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(PartType.id, PartType.type_name, PartType.type_unit))
        results = connection.execute(stmt).fetchall()
        return results

    # Get part types by name
    @db_connector
    def get_part_type_by_name(self, type_name: str, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(Part.id, Part.name, Part.amount, Part.part_number,
                Part.part_store_name, Part.type, Part.unit).where(Part.type == type_name))
        results = connection.execute(stmt).fetchall()
        return results

    # Checks to see if the part_store_name exists in the database already
    @db_connector
    def check_duplicates(self, part_store_name: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')
        stmt = (select(PartStore.part_store_name))
        results = connection.execute(stmt).fetchall()
        res = [i[0] for i in results]
        if res.count(part_store_name) > 0:
            return False
        return True

    # Get password by username
    @db_connector
    def get_password_by_username(self, username: str, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(Account.id, Account.username, Account.password,
                Account.is_admin, Account.is_confirmed).where(Account.username == username))
        username_res = connection.execute(stmt).fetchall()
        fin_res = [i[2] for i in username_res]
        return fin_res

    # Get the unit by the part name
    @db_connector
    def get_unit_by_part(self, part_type: str, **kwargs) -> list:
        connection = kwargs.pop('connection')
        sql = (select(PartType.type_unit).where(
            PartType.type_name == part_type))
        results = connection.execute(sql).fetchone()
        res = [i for i in results]
        return res

    # Check if account exists in the database
    @db_connector
    def check_if_account_exists(self, username: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')
        stmt = (select(Account.id, Account.username, Account.password,
                Account.is_admin, Account.is_confirmed).where(Account.username == username))
        get_username_results = connection.execute(stmt).fetchall()
        if not get_username_results:
            return False
        return True

    # Check if duplicates exist in the database
    @db_connector
    def get_dupes(self, query_table: object, row_to_find: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')

        # Use the distinct select statement in the parts DB
        get_stores_dist = (select(distinct(query_table)).order_by(query_table))
        dist_results = connection.execute(get_stores_dist).fetchall()

        # List the results in an array
        fin_dist = [i[0] for i in dist_results]

        # Use the list of duplicates to see if the part store exists in the part store DB
        get_duplicates = (select(query_table))
        dupe_results = connection.execute(get_duplicates).fetchall()

        # List the results in an array
        fin_dupes = [i[0] for i in dupe_results]

        # If the part_store_name exists in either database, return True; otherwise return False
        if fin_dist.count(row_to_find) > 0 or row_to_find in fin_dupes:
            return True
        return False

    # Check if the part store exists and has a part within it from either the parts or part store DB
    def check_if_exists(self, part_store_name: str) -> bool:
        return self.get_dupes(PartStore.part_store_name, part_store_name)

    # Check if part type exists
    def check_if_type_exists(self, part_type: str) -> bool:
        return self.get_dupes(PartType.type_name, part_type)

    # Insert part store into the database
    @db_connector
    def insert_part_store(self, part_store_name: str, part_store_icon: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        if check_input(part_store_name) and check_input(part_store_icon):
            stmt = (insert(PartStore).values(
                part_store_name=part_store_name, icon=part_store_icon))
            connection.execute(stmt)
            connection.commit()

    # Get all part stores by part store name
    @db_connector
    def get_part_stores(selfself, part_store_name: int, **kwargs) -> tuple or None:
        connection = kwargs.pop('connection')
        stmt = select(Part.id, Part.name, Part.amount, Part.part_number, Part.part_store_name,
                      Part.type, Part.unit).where(Part.part_store_name == part_store_name)
        results = connection.execute(stmt).fetchall()

        # If the results are empty (i.e. the part_store_name doesn't exist) return None
        if not results:
            return None
        return results

    # Get list of part store names that exist in the database
    @db_connector
    def get_part_store_names(self, **kwargs) -> tuple:
        connection = kwargs.pop('connection')
        stmt = select(PartStore.id, PartStore.part_store_name, PartStore.icon) \
            .order_by(cast(PartStore.part_store_name, Integer))
        results = connection.execute(stmt).fetchall()
        return results

    # Get the selections from the part store names that currently exist in the database
    def get_selections(self) -> list:
        results = self.get_part_store_names()
        re = [(g[1], g[1]) for g in results]
        return re

    # Insert entries into database
    @db_connector
    def insert(self, part_name: str, part_amount: str, part_number: str, part_store_name: str, part_type: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        if check_input(part_name) and check_input(part_amount) and part_amount.isnumeric() and check_input(part_number) and check_input(part_store_name) and check_input(part_type):
            stmt = (insert(Part).values(name=part_name, amount=part_amount, part_number=part_number,
                                        part_store_name=part_store_name, type=part_type,
                                        unit=self.get_unit_by_part(part_type)))
            connection.execute(stmt)
            connection.commit()

    # Insert part type into the database
    @db_connector
    def insert_part_type(self, part_type: str, part_unit: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        if check_input(part_type) and check_input(part_unit) and not self.check_if_type_exists(part_type):
            stmt = (insert(PartType).values(
                type_name=part_type, type_unit=part_unit))
            connection.execute(stmt)
            connection.commit()

     # Make sure the phone number is not in the database
    @db_connector
    def check_if_phone_num_exists(self, phone_num: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')
        stmt = (select(Account.phone_num).where(
            Account.phone_num == phone_num))
        results = connection.execute(stmt).fetchall()
        if results:
            return True
        return False

    # Send text to the username supplied with the amount of low parts in the system
    @db_connector
    def send_text(self, username: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')

        # Get the phone number by username
        stmt = (select(Account.phone_num).where(Account.username == username))
        phone_num = [i[0] for i in connection.execute(stmt).fetchall()]

        # Line to separate each row for readability
        line = '-' * 20
        low_parts = ['Part Name: ' + str(i[1]) + ' \nPart Number: ' + str(i[3]) + '\nPart Store Name: ' + str(i[4]) +
                     '\nCurrent Amount: ' +
                     str(i[2]) + '\nPart Threshold: ' + str(i[5]) + '\n' + line
                     for i in self.get_low_parts()]
        message = line + '\n' + '\n'.join(low_parts)

        # Send the message
        send = post(url=environ.get('TILL_URL'),
                    headers={'Content-Type': 'application/json'},
                    json={'phone': ['1' + phone_num[0]],
                          'method': 'SMS',
                          'text': message})

        if send.status_code == 200:
            return True
        return False

    # Delete part type from database by ID
    @db_connector
    def delete_part_type(self, type_id: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (delete(PartType).where(PartType.id == type_id))
        connection.execute(stmt)
        connection.commit()

    # Update part type
    @db_connector
    def update_part_type(self, type_id: str, type_name: str, type_unit: str, **kwargs) -> None:
        connection = kwargs.pop('connection')

        if check_input(type_name) and check_input(type_unit) and not self.check_if_type_exists(type_name.lower()):
            stmt = (update(PartType).values(type_name=type_name,
                    type_unit=type_unit).where(PartType.id == type_id))
            connection.execute(stmt)
            connection.commit()

    # Get part information by part id
    @db_connector
    def get_part_information(self, part_id: str, **kwargs) -> tuple:
        connection = kwargs.pop('connection')
        stmt = (
            select(Part.id, Part.name, Part.amount, Part.part_number, Part.part_store_name, Part.low_thresh, Part.type,
                   Part.unit).where(Part.id == part_id))
        results = connection.execute(stmt).fetchall()
        return results

    # Delete entries from database by ID
    @db_connector
    def delete(self, row_id: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (delete(Part).where(Part.id == int(row_id)))
        connection.execute(stmt)
        connection.commit()

    # Update entries from database by ID
    @db_connector
    def update(self, row_id: str, part_name: str, part_amount: str, part_number: str, part_store_name: str, part_type: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (update(Part).values(name=part_name, amount=part_amount,
                                    part_number=part_number, part_store_name=part_store_name,
                                    type=part_type, unit=self.get_unit_by_part(part_type))
                .where(Part.id == row_id))

        if check_input(part_name) and check_input(part_amount) and check_input(part_number) and check_input(part_store_name) and check_input(part_type):
            connection.execute(stmt)
            connection.commit()

    # Delete part store by part_store_id
    @db_connector
    def delete_part_store(self, part_store_id: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (delete(PartStore).where(PartStore.id == part_store_id))
        connection.execute(stmt)
        connection.commit()

    # Update part_store by part_store_id
    @db_connector
    def update_part_store(self, part_store_id: str, part_store_name: str, part_store_image: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        current_name, current_icon = get_current_store_name_icon(part_store_id)

        # Check for duplicates and validate input
        if part_store_name == current_name and part_store_image != current_icon \
                and check_if_icon_exists(part_store_image):
            stmt = (update(PartStore).values(icon=part_store_image)
                    .where(PartStore.id == part_store_id))
            connection.execute(stmt)
            connection.commit()
        elif part_store_name != current_name and part_store_image == current_icon and \
                check_input(part_store_name) and self.check_duplicates(part_store_name):
            stmt = (update(PartStore).values(part_store_name=part_store_name)
                    .where(PartStore.id == part_store_id))
            connection.execute(stmt)
            connection.commit()
        else:
            if check_input(part_store_name) and self.check_duplicates(part_store_name):
                stmt = (update(PartStore).values(part_store_name=part_store_name, icon=part_store_image)
                        .where(PartStore.id == part_store_id))
                connection.execute(stmt)
                connection.commit()

    # Update part's threshold
    @db_connector
    def update_threshold(self, thresh: int or str, part_id: int, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (update(Part).values(low_thresh=thresh).where(Part.id == part_id))
        connection.execute(stmt)
        connection.commit()

    # Get table of low parts
    @db_connector
    def get_low_parts(self, **kwargs) -> tuple:
        connection = kwargs.pop('connection')
        stmt = (select(Part.id, Part.name, Part.amount, Part.part_number, Part.part_store_name, Part.low_thresh)
                .where(Part.low_thresh > Part.amount))
        results = connection.execute(stmt).fetchall()
        return results

    # Check if account is confirmed
    @db_connector
    def check_if_confirmed(self, username: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')
        stmt = (select(Account.is_confirmed).where(
            Account.username == func.lower(username)))
        results = connection.execute(stmt).fetchone()
        res = ''.join(map(str, str(results)))
        if int(res[1]) == 1:
            return True
        return False

    # Confirm account by ID
    @db_connector
    def confirm_account(self, user_id: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (update(Account).values(
            {'is_confirmed': 1}).where(Account.id == user_id))
        connection.execute(stmt)
        connection.commit()

    # Delete account by ID
    @db_connector
    def delete_account(self, user_id: str, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (delete(Account).where(Account.id == user_id))
        connection.execute(stmt)
        connection.commit()

    # Login by username and password
    def login(self, username: str, password: str) -> bool:
        hash_pw = self.get_password_by_username(username)
        if hash_pw and check_password_hash(password.encode('utf8'), hash_pw[0].encode('utf8')) \
                and self.check_if_account_exists(username) and self.check_if_confirmed(username):
            return True
        return False

    # Register by username, password, and conf_password
    @db_connector
    def register(self, username: str, password: str, conf_password: str, phone_num: str, **kwargs) -> int:
        connection = kwargs.pop('connection')

        if check_password(password, conf_password) and check_input(password) and check_input(conf_password) and not self.check_if_account_exists(username) and not self.check_if_phone_num_exists(phone_num):
            hashed_pw = create_password_hash(password.encode('utf-8'))

            if check_password_hash(password.encode('utf-8'), hashed_pw) and check_phone_num(phone_num):
                stmt = (insert(Account).values(username=username,
                        password=hashed_pw, phone_num=phone_num))

                connection.execute(stmt)
                connection.commit()
                return 200
            return 422
        return 409

    # Check if user is an admin by username
    @db_connector
    def check_admin(self, username: str, **kwargs) -> bool:
        connection = kwargs.pop('connection')
        stmt = (select(Account.is_admin).where(
            func.lower(Account.username) == username))
        results = connection.execute(stmt).fetchone()
        res = ''.join(map(str, str(results[0])))
        return True if int(res) == 1 else False

    # Make / remove user from admin
    @db_connector
    def modify_admin(self, user_id: str, value: str or int, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (update(Account).values(
            is_admin=value).where(Account.id == user_id))
        connection.execute(stmt)
        connection.commit()

    # Get users that exist in the DB excluding the current user's username
    @db_connector
    def get_users(self, username: str, **kwargs) -> list:
        connection = kwargs.pop('connection')
        stmt = (select(Account.id, func.lower(Account.username), Account.is_admin, Account.is_confirmed,
                       Account.phone_num).where(Account.username != func.lower(username)))
        res = [list(i) for i in connection.execute(stmt).fetchall()]

        # Make the phone number more readable
        for x in res:
            x[4] = (format(int(x[4][:-1]), ',').replace(',', '-') + x[4][-1])
        return res

    # Get parts by part store name
    @db_connector
    def get_parts_by_store(self, part_store_name: str, **kwargs) -> tuple:
        connection = kwargs.pop('connection')
        stmt = (select(Part.id, Part.name, Part.amount, Part.part_number)
                .where(Part.part_store_name == part_store_name))
        results = connection.execute(stmt).fetchall()
        return results

    # Update multiple parts according to the part store name
    @db_connector
    def update_multiple_parts_by_part_store(self, values: list, **kwargs) -> None:
        connection = kwargs.pop('connection')

        for item in values:
            stmt = (update(Part).values(
                amount=item[0]).where(Part.id == item[1]))
            connection.execute(stmt)
            connection.commit()

    # Record a new job in the database
    @db_connector
    def record_job(self, username: str, time: str, part_store_name: str, parts_used: str or int, **kwargs) -> None:
        connection = kwargs.pop('connection')
        stmt = (insert(Job).values(username=func.lower(username), time=time,
                part_store_name=part_store_name, parts_used=parts_used))
        connection.execute(stmt)
        connection.commit()

    # Get all jobs from database
    @db_connector
    def get_jobs(self, **kwargs) -> tuple:
        connection = kwargs.pop('connection')
        stmt = (select(Job.job_id, Job.username, Job.time,
                Job.part_store_name, Job.parts_used))
        results = connection.execute(stmt).fetchall()
        return results

    # Get the total amount of parts by part store
    @db_connector
    def get_total_parts_by_part_store(self, part_store_name: int, **kwargs) -> int:
        connection = kwargs.pop('connection')
        stmt = (select(func.sum(Part.amount)).where(
            Part.part_store_name == part_store_name))
        results = connection.execute(stmt).fetchall()
        res = [i[0] for i in results]
        return res[0]

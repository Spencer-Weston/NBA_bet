"""
Author: Spencer Weston

Purpose: This file contains functions for working with databases. It works with SQL lite databases and uses the
sqlalchemy package to construct the functions.

To-do:
    In all likelihood, many of these functions should be contained in a class. The conversion will need to be studied
    a bit to figure out the optimal structure. But in general, a database class should have access to all tables within
    it. Those tables should likely be classes themselves with associated functions.
"""

import datetime
from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Boolean, Table
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, mapper, clear_mappers

# local imports
import general


# Type conversion functions (python types, sql types, sqlalchemy types)
def get_py_type(tbl_dict):
    """Take a table dictionary with data values and return a dictionary that holds the python type for the dict values.

    Args:
        tbl_dict: a table dictionary formatted as key:[list] where the list holds data values

    Returns:
        A dictionary formatted as key:py_type where the type can be integer, float, string, datetime, or none
    """
    tbl_keys = list(tbl_dict.keys())
    py_types = [general.get_type(tbl_dict[key]) for key in tbl_keys]
    py_types_dict = dict(zip(tbl_keys, py_types))
    return py_types_dict


def get_sql_type(tbl_dict):
    """Take a table dictionary with data values and return a dictionary that holds the sql type for the dict values.

    Args:
        tbl_dict: a table dictionary formatted as key:[list] where the list holds data values

    Returns:
        A dictionary with the same keys as tbl_dict. The dictionary's values are the sql_types of each key:value pair in
        tbl_dict. The sql_types are defined to function with sqlalchemy.
    """
    py_types = get_py_type(tbl_dict)  # py_types is a dict
    sql_types = py_type_to_sql_type(py_types)
    return sql_types


def py_type_to_sql_type(py_types):
    """Convert and return a dictionary of python types to a dictionary of sql types.

    Raises:
        An exception if a py_type is not an integer, float, string, datetime, bool, or none

    To-do:
        Change the logic into a switch statement
    """

    sql_types = dict()
    for key in py_types:
        py_type = py_types[key]
        if py_type == "integer" or py_type is int:
            sql_types[key] = Integer
        elif py_type == "float" or py_type is float:
            sql_types[key] = Float
        elif py_type == "string" or py_type is str:
            sql_types[key] = String
        elif py_type == "datetime" or py_type is datetime.datetime:
            sql_types[key] = DateTime
        elif py_type == "bool" or py_type is bool:
            sql_types[key] = Boolean
        elif py_type is None:
            continue  # We continue here so as to not create a column for null values
        else:
            raise Exception("Error: py_type {} is not an integer, float, datetime,"
                            " none, or string".format(py_types[key]))
    return sql_types


def create_col_definitions(tbl_name, id_type_dict, foreign_key=False):
    """Create and return a dictionary of column specifications for a sql_alchemy table.

    Returns a dictionary that begins with __table__name and an integer id followed by columns as specified
    in the id_type_dict

    Args:
        tbl_name: name of the table to create column definitions for
        id_type_dict: dictionary of column id's as keys and sql_alchemy sql types as values
        foreign_key: To add a foreign key column, pass a string formatted as foreign "table.column"
    Returns:
        Column definitions
    """
    col_specs = {'__tablename__': '{}'.format(tbl_name),
                 'id': Column(Integer, primary_key=True)}
    if foreign_key:
        col_specs[foreign_key] = Column(foreign_key, Integer, ForeignKey(foreign_key), nullable=False, unique=True)
    for key in id_type_dict:
        col_specs[key] = Column(id_type_dict[key])

    return col_specs


class Database:
    """Database is the highest level in a hierarchy of classes which deal with database interactions with sqlalchemy

    Database serves as the hub for high level attributes such as the Base and engine which apply to all tables in the
    database. """
    class Template(object):
        """Blank template to map tables to with the sqlalchemy mapper function"""
        pass

    def __init__(self, url):
        """Creates an engine on the specified path, generates a declarative Base class which reflects the engine
        The base is passed to subclasses in order to generate tables. The session allows interaction with the DB."""
        self.path = url
        self.engine = create_engine(self.path)
        self.conn = self.engine.connect()
        self.metadata = MetaData(self.engine)
        self.Base = declarative_base()
        self.table_names = list(self.get_tables())
        #self.table_interfaces = {table: self.get_interface(table) for table in self.table_names}

    def get_interface(self, name):
        return TableInterface(name, self.path)

    def get_tables(self, table_names=False):
        """Find and returns the specified tables or returns all tables """
        meta = MetaData(bind=self.engine)
        meta.reflect(bind=self.engine)
        if table_names:
            return meta.tables[table_names]
        else:
            return meta.tables

    def create_table(self):
        """Creates all tables which have been made with the Base class of the Database"""
        self.metadata.create_all(self.engine)

    def map_table(self, tbl_name, column_types):
        """Maps a dictionary keyed on column names with Type values to the TableInterface Template"""
        t = Table(tbl_name, self.metadata, Column('id', Integer, primary_key=True),
                  *(Column(key, value) for key, value in column_types.items()))

        mapper(self.Template, t)

    def clear_mappers(self):
        clear_mappers()

    def insert_row(self, engine, table, row):
        """Insert a single row into the specified table in the engine"""
        conn = engine.connect()
        conn.execute(table.insert(), row)
        # Rows formatted as
        #   [{'l_name': 'Jones', 'f_name': 'bob'},
        #   {'l_name': 'Welker', 'f_name': 'alice'}])

    def insert_rows(self, table, rows):
        """Inserts the rows into the specified table in the engine

        To-do:
            Concatenate rows so that only one call to the DB is made when inserting. (I don't remember exactly what I meant
            by this.
        """
        table = self.get_tables(table)
        for row in rows:
            self.conn.execute(table.insert(), row)

# class Table(declarative_base()):
#     __tablename__ = "test"
#     id = Column("some_table_id", Integer, primary_key=True)


class TableInterface(Database):
    """TableInterface operates with individual Table classes with attributes inherited from Database"""


    def __init__(self, table_name, url):
        super().__init__(url)
        self.name = table_name
        self.table_names.append(self.name)
        # if self.table_exists():
        #    pass

    def map_table(self, column_types):
        """Maps a dictionary keyed on column names with Type values to the TableInterface Template"""
        t = Table(self.name, self.metadata, Column('id', Integer, primary_key=True),
                  *(Column(key, value) for key, value in column_types.items()))

        mapper(self.Template, t)

    def return_table(self):
        return self.Template


def drop_table(self, engine, drop_tbl):
    """Input an engine, find the drop_tbl in the engine metadata, and drop the drop_tbl from the engine"""

    meta = MetaData(bind=engine)
    meta.reflect(bind=engine)
    drop_tbl_class = meta.tables[drop_tbl]
    drop_tbl_class.drop()

def table_exists(self):
    meta = MetaData(bind=self.engine)
    meta.reflect(bind=self.engine)
    if self.name in meta.tables:
        return True
    else:
        return False

def get_table(self, engine, tbl):
    """Find the specified table in the engine and returns the table"""
    meta = MetaData(bind=engine)
    meta.reflect(bind=engine)
    return meta.tables[tbl]


# Table modification functions
def dict_to_rows(tbl):
    """Convert and return an input dictionary into rows compatible with sqlalchemy's insert function

    Currently presumes each dictionary object is a list of equivalent length. Calls _dict_to_rows() to do primary
    processing. Does not yet function with lists.

    Returns:
        a list of rows compatible with sqlalchemy's insert function

    Raise:
        Exception: If the input is neither a list nor dictionary, an exception is raised
    """
    if isinstance(tbl, dict):
        return _dict_to_rows(tbl)
    elif isinstance(tbl, list):
        return _list_to_rows(tbl)
    else:
        raise Exception("tbl is neither a list or dictionary, and cannot be handled")


def _dict_to_rows(tbl):
    """Convert and return an input dictionary into rows compatible with sqlalchemy's insert function"""

    rows = []
    keys = list(tbl.keys())
    length = len(tbl[keys[0]])  # The length of the data; should be checked outside the function for equivalent length
    for i in range(length):
        row_dict = dict()
        for key in keys:
            row_dict[key] = tbl[key][i]
        rows.append(row_dict)
    return rows


def _list_to_rows(tbl):
    """Not yet functional

    To-do:
        Implement functionality for transforming lists into database rows"""

    raise Exception("tbl is a list. Function to convert lists into database rows is not implemented")


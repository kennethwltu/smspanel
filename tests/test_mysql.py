def test_pymysql_available():
    """PyMySQL should be available for MySQL connections."""
    import pymysql

    assert pymysql is not None

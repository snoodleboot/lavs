import duckdb


conn = duckdb.connect("../../../../code/lavs/app/test.db")
try:

    with open("../ddl.sql", "r") as stream:
        query = "".join(stream.readlines())

    print(query)
    conn.execute(query=query)

    df = conn.execute("SELECT COUNT(*) as COUNT FROM VERSIONS").fetchdf()
    print(df.head())
finally:
    conn.close()

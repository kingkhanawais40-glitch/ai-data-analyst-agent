from backend.database import PostgresCursor


class FakeCursor:
    def __init__(self, returned_row=None):
        self.statement = None
        self.parameters = None
        self.returned_row = returned_row

    def execute(self, statement, parameters=None):
        self.statement = statement
        self.parameters = parameters

    def fetchone(self):
        return self.returned_row


def test_question_mark_placeholders_convert_to_postgres():
    fake = FakeCursor()
    cursor = PostgresCursor(fake)

    cursor.execute(
        "SELECT * FROM datasets WHERE id = ? AND name = ?",
        (12, "power"),
    )

    assert fake.statement == (
        "SELECT * FROM datasets WHERE id = %s AND name = %s"
    )
    assert fake.parameters == (12, "power")


def test_dataset_insert_returns_inserted_id():
    fake = FakeCursor(returned_row={"id": 101})
    cursor = PostgresCursor(fake)

    cursor.execute(
        """
        INSERT INTO datasets (name, file_name)
        VALUES (?, ?)
        """,
        ("Power Data", "power.xlsx"),
    )

    assert "RETURNING ID" in fake.statement.upper()
    assert fake.parameters == ("Power Data", "power.xlsx")
    assert cursor.lastrowid == 101


def test_analysis_history_insert_returns_inserted_id():
    fake = FakeCursor(returned_row={"id": 202})
    cursor = PostgresCursor(fake)

    cursor.execute(
        """
        INSERT INTO analysis_history (dataset_id, question, answer)
        VALUES (?, ?, ?)
        """,
        (101, "Average consumption?", "42.5"),
    )

    assert "RETURNING ID" in fake.statement.upper()
    assert fake.parameters == (
        101,
        "Average consumption?",
        "42.5",
    )
    assert cursor.lastrowid == 202


def test_insert_with_existing_returning_does_not_append_another():
    fake = FakeCursor()
    cursor = PostgresCursor(fake)

    cursor.execute(
        "INSERT INTO datasets (name) VALUES (?) RETURNING id",
        ("Power Data",),
    )

    assert fake.statement.upper().count("RETURNING") == 1
    assert cursor.lastrowid is None


def test_non_insert_does_not_add_returning_id():
    fake = FakeCursor()
    cursor = PostgresCursor(fake)

    cursor.execute(
        "UPDATE datasets SET name = ? WHERE id = ?",
        ("Updated", 101),
    )

    assert "RETURNING id" not in fake.statement.upper()
    assert cursor.lastrowid is None


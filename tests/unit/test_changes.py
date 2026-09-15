from pathlib import Path

from testbreaker.changes import parse_changed_files
from testbreaker.domain import ChangedFile


def test_parse_replacement_uses_new_side_line_number():
    diff = """\
diff --git a/refund.py b/refund.py
--- a/refund.py
+++ b/refund.py
@@ -10 +10 @@
-    return days <= 30
+    return days < 30
"""

    assert parse_changed_files(diff) == [ChangedFile(Path("refund.py"), (10,))]


def test_parse_multiple_files_and_hunks_aggregates_sorted_lines():
    diff = """\
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -8,0 +9 @@
+    second = 2
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -4 +4 @@
-    first = 0
+    first = 1
@@ -19,0 +20 @@
+    third = 3
"""

    assert parse_changed_files(diff) == [
        ChangedFile(Path("a.py"), (4, 20)),
        ChangedFile(Path("b.py"), (9,)),
    ]


def test_parse_deleted_only_hunk_anchors_to_following_new_line():
    diff = """\
diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -2 +1,0 @@ def foo():
-    debug()
"""

    assert parse_changed_files(diff) == [ChangedFile(Path("app.py"), (2,))]


def test_parse_ignores_non_python_files():
    diff = """\
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old
+new
"""

    assert parse_changed_files(diff) == []

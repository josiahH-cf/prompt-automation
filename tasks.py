from invoke import task

@task
def lint(c):
    c.run("ruff src tests")
    c.run("mypy src")

@task
def test(c):
    c.run("pytest --cov=src --cov-report=term")

@task
def build(c):
    c.run("python -m build")

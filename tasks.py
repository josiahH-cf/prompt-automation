from invoke import task

@task
def lint(c):
    c.run("ruff src tests")

@task
def test(c):
    c.run("pytest --cov=src --cov-report=term")

@task
def build(c):
    c.run("python -m build")

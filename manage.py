import asyncio
import typer
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.database import get_session, engine
from app.models.models import User
from app.api.v1.auth import get_password_hash


app = typer.Typer()


@app.command()
def create_admin(username: str = "admin", password: str = "admin123", email: str = "admin@example.com", role: str = "admin"):
    """
    CLI command to create a new admin user.
    Usage: python manage.py create-admin --username myadmin --password secret
    """
    async def create():
        async with AsyncSession(engine) as session:
            hashed_pwd = get_password_hash(password)

            new_admin = User(
                username=username,
                email=email,
                full_name=username,
                roles=[role],
                hashed_password=hashed_pwd
            )

            try:
                session.add(new_admin)
                await session.commit()
                typer.echo(f"Successfully created {username}")
            except Exception as e:
                typer.echo(f"Error: {e}")

    asyncio.run(create())


if __name__ == "__main__":
    app()

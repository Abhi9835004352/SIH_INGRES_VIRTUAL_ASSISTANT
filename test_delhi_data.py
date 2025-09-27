
import asyncio
from app.database import db_manager

async def main():
    await db_manager.initialize()
    data = await db_manager.query_groundwater_data(state='DELHI')
    print(data)

if __name__ == "__main__":
    asyncio.run(main())

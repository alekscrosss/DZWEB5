import aiohttp
import asyncio
import sys
from datetime import datetime, timedelta
import websockets
from aiofile import async_open

BASE_URL = "https://api.privatbank.ua/p24api/exchange_rates?json&date="

async def fetch_rate(session, date, currencies):
    url = f"{BASE_URL}{date.strftime('%d.%m.%Y')}"
    async with session.get(url) as response:
        data = await response.json()
        rates = {
            currency: next(
                (item for item in data["exchangeRate"] if item.get("currency") == currency),
                None
            ) for currency in currencies
        }
        return {date.strftime('%d.%m.%Y'): rates}


async def fetch_rates_for_days(days, currencies):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            tasks.append(fetch_rate(session, date, currencies))
        return await asyncio.gather(*tasks)


async def log_command_usage(command):
    async with async_open("exchange_log.txt", "a") as log_file:
        await log_file.write(f"{command} command used at {datetime.now()}\n")


async def exchange_rates_command(websocket, path):
    async for message in websocket:
        if message.startswith("exchange"):
            args = message.split()
            if len(args) >= 2:
                days = min(int(args[1]), 10)  # Ensure it does not exceed 10 days
                currencies = args[2:] if len(args) > 2 else ['USD', 'EUR']
                rates = await fetch_rates_for_days(days, currencies)
                await websocket.send(str(rates))
                await log_command_usage("exchange")


# Running the chat server
async def main():
    if len(sys.argv) >= 2:
        days = min(int(sys.argv[1]), 10)
        currencies = sys.argv[2:] if len(sys.argv) > 2 else ['USD', 'EUR']
        rates = await fetch_rates_for_days(days, currencies)
        print(rates)
    else:
        # If no arguments provided, start the chat server
        server = await websockets.serve(exchange_rates_command, "localhost", 6789)
        await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())

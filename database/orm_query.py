from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Bank, StockMarket, Cryptocurrency, CryptoMarket, Account, Currency, Deposit, Share, \
    Fund, Banner


async def orm_add_banner_description(session: AsyncSession, data: dict):
    result = await session.execute(select(Banner))
    if result.first():
        return
    session.add_all([Banner(name=name, description=description) for name, description in data.items()])
    await session.commit()


async def orm_change_banner_image(session: AsyncSession, name: str, image: str):
    result = update(Banner).where(Banner.name == name).values(image=image)
    await session.execute(result)
    await session.commit()


async def orm_get_banner(session: AsyncSession, page: str):
    result = await session.execute(select(Banner).where(Banner.name == page))
    return result.scalar()


async def orm_get_info_pages(session: AsyncSession):
    query = select(Banner)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_add_user(session: AsyncSession, message):
    exciting_user = await session.execute(select(User).where(User.user_tg_id == message.from_user.id))
    user_in_db = exciting_user.scalars().first()
    if user_in_db:
        return

    obj = User(
        user_tg_id=message.from_user.id,
        username=message.from_user.full_name
    )
    session.add(obj)
    await session.commit()

async def orm_get_user(sesion: AsyncSession, user_id: int):
    result = await sesion.execute(select(User.id).where(User.user_tg_id == user_id))
    return result.scalar()


async def orm_add_bank(session: AsyncSession, data: dict, message):
    result = await session.execute(select(User.id).where(User.user_tg_id == message.from_user.id))
    user_id = result.scalars().first()
    obj = Bank(
        name=data["name"],
        user_id=user_id
    )
    session.add(obj)
    await session.commit()


async def orm_get_bank_by_id(session: AsyncSession, bank_id: int):
    result = await session.execute(select(Bank).where(Bank.id == bank_id))
    return result.scalars().first()


async def orm_get_bank(session: AsyncSession, user_id: int):
    result = await session.execute(select(Bank).where(Bank.user_id == user_id))
    return result.scalars().all()


async def orm_update_bank(session: AsyncSession, bunk_id: int, data):
    query = update(Bank).where(Bank.id == bunk_id).values(
        name=data["name"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_bank(session: AsyncSession, bank_id: int):
    query = delete(Bank).where(Bank.id == bank_id)
    await session.execute(query)
    await session.commit()


async def orm_add_stock_market(session: AsyncSession, data: dict, message):
    result = await session.execute(select(User.id).where(User.user_tg_id == message.from_user.id))
    user_id = result.scalars().first()
    obj = StockMarket(
        name=data["name"],
        user_id=user_id
    )
    session.add(obj)
    await session.commit()


async def orm_get_stock_market_by_id(session: AsyncSession, stockmarket_id:int):
    result = await session.execute(select(StockMarket).where(StockMarket.id == stockmarket_id))
    return result.scalars().first()


async def orm_get_stock_market(session: AsyncSession, user_id: int):
    result = await session.execute(select(StockMarket).where(StockMarket.user_id == user_id))
    return result.scalars().all()


async def orm_update_stock_market(session: AsyncSession, stockmarket_id: int, data):
    query = update(StockMarket).where(StockMarket.id == stockmarket_id).values(
        name=data["name"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_stock_market(session: AsyncSession, stockmarket_id: int):
    query = delete(StockMarket).where(StockMarket.id == stockmarket_id)
    await session.execute(query)
    await session.commit()


async def orm_add_cryptomarket(session: AsyncSession, data: dict, message):
    result = await session.execute(select(User.id).where(User.user_tg_id == message.from_user.id))
    user_id = result.scalars().first()
    obj = CryptoMarket(
        name=data["name"],
        user_id=user_id
    )
    session.add(obj)
    await session.commit()



async def orm_get_cryptomarket_by_id(session: AsyncSession, cryptomarket_id: int):
    result = await session.execute(select(CryptoMarket).where(CryptoMarket.id == cryptomarket_id))
    return result.scalars().first()


async def orm_get_cryptomarket(session: AsyncSession, user_id: int):
    result = await session.execute(select(CryptoMarket).where(CryptoMarket.user_id == user_id))
    return result.scalars().all()


async def orm_update_cryptomarket(session: AsyncSession, cryptomarket_id: int, data):
    query = update(CryptoMarket).where(CryptoMarket.id == cryptomarket_id).values(
        name=data["name"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_cryptomarket(session: AsyncSession, cryptomarket_id: int):
    query = delete(CryptoMarket).where(CryptoMarket.id == cryptomarket_id)
    await session.execute(query)
    await session.commit()


# сделать проверку на созданный банк
async def orm_add_account(session: AsyncSession, data: dict):
    obj = Account(
        name=data["name"],
        balance=float(data["balance"]),
        bank_id=int(data["bank_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_account(session: AsyncSession, account_id: int):
    result = await session.execute(select(Account).where(Account.id == account_id))
    return result.scalars().first()


async def orm_get_account_by_bank_id(session: AsyncSession, bank_id: int):
    result = await session.execute(select(Account).where(Account.bank_id == bank_id))
    return result.scalars().all()


async def orm_update_account(session: AsyncSession, account_id: int, data):
    query = update(Account).where(Account.id == account_id).values(
        name=data["name"],
        balance=data["balance"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_account(session: AsyncSession, account_id: int):
    query = delete(Account).where(Account.id == account_id)
    await session.execute(query)
    await session.commit()


async def orm_add_currency(session: AsyncSession, data: dict):
    obj = Currency(
        name=data["name"],
        balance=float(data["balance"]),
        market_price=float(data["market_price"]),
        bank_id=int(data["bank_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_currency(session: AsyncSession, currency_id: int):
    result = await session.execute(select(Currency).where(Currency.id == currency_id))
    return result.scalars().first()


async def orm_get_currency_by_bank_id(session: AsyncSession, bank_id: int):
    result = await session.execute(select(Currency).where(Currency.bank_id == bank_id))
    return result.scalars().all()


async def orm_update_currency(session: AsyncSession, currency_id: int, data):
    query = update(Currency).where(Currency.id == currency_id).values(
        name=data["name"],
        balance=data["balance"],
        market_price=data["market_price"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_currency(session: AsyncSession, currency_id: int):
    query = delete(Currency).where(Currency.id == currency_id)
    await session.execute(query)
    await session.commit()


async def orm_add_deposit(session: AsyncSession, data: dict):
    obj = Deposit(
        name=data["name"],
        start_date=data['start_date'],
        deposit_term=int(data["deposit_term"]),
        interest_rate=float(data["interest_rate"]),
        balance=float(data["balance"]),
        bank_id=int(data["bank_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_deposit(session: AsyncSession, deposit_id: int):
    result = await session.execute(select(Deposit).where(Deposit.id == deposit_id))
    return result.scalars().first()


async def orm_get_deposit_by_bank_id(session: AsyncSession, bank_id: int):
    result = await session.execute(select(Deposit).where(Deposit.bank_id == bank_id))
    return result.scalars().all()


async def orm_update_deposit(session: AsyncSession, deposit_id: int, data):
    query = update(Deposit).where(Deposit.id == deposit_id).values(
        name=data["name"],
        start_date=data["start_date"],
        deposit_term=data["deposit_term"],
        interest_rate=data["interest_rate"],
        balance=data["balance"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_deposit(session: AsyncSession, deposit_id: int):
    query = delete(Deposit).where(Deposit.id == deposit_id)
    await session.execute(query)
    await session.commit()


# сделать проверку на созданную биржу
async def orm_add_share(session: AsyncSession, data: dict):
    obj = Share(
        name=data["name"],
        purchase_price=float(data["purchase_price"]),
        selling_price=float(data["selling_price"]),
        market_price=float(data["market_price"]),
        quantity=int(data["quantity"]),
        stockmarket_id=int(data["stockmarket_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_share(session: AsyncSession, share_id: int):
    result = await session.execute(select(Share).where(Share.id == share_id))
    return result.scalars().first()


async def orm_get_share_by_stockmarket_id(session: AsyncSession, stockmarket_id: int):
    result = await session.execute(select(Share).where(Share.stockmarket_id == stockmarket_id))
    return result.scalars().all()


async def orm_update_share(session: AsyncSession, share_id: int, data):
    query = update(Share).where(Share.id == share_id).values(
        name=data["name"],
        purchase_price=data["purchase_price"],
        selling_price=data["selling_price"],
        market_price=data["market_price"],
        quantity=data["quantity"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_share(session: AsyncSession, share_id: int):
    query = delete(Share).where(Share.id == share_id)
    await session.execute(query)
    await session.commit()


async def orm_add_fund(session: AsyncSession, data: dict):
    obj = Fund(
        name=data["name"],
        purchase_price=float(data["purchase_price"]),
        selling_price=float(data["selling_price"]),
        market_price=float(data["market_price"]),
        quantity=int(data["quantity"]),
        stockmarket_id=int(data["stockmarket_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_fund(session: AsyncSession, fund_id: int):
    result = await session.execute(select(Fund).where(Fund.id == fund_id))
    return result.scalars().first()


async def orm_get_fund_by_stockmarket_id(session: AsyncSession, stockmarket_id: int):
    result = await session.execute(select(Fund).where(Fund.stockmarket_id == stockmarket_id))
    return result.scalars().all()


async def orm_update_fund(session: AsyncSession, fund_id: int, data):
    query = update(Fund).where(Fund.id == fund_id).values(
        name=data["name"],
        purchase_price=data["purchase_price"],
        selling_price=data["selling_price"],
        market_price=data["market_price"],
        quantity=data["quantity"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_fund(session: AsyncSession, fund_id: int):
    query = delete(Fund).where(Fund.id == fund_id)
    await session.execute(query)
    await session.commit()


async def orm_add_cryptocurrency(session: AsyncSession, data: dict):
    obj = Cryptocurrency(
        name=data["name"],
        balance=float(data["balance"]),
        purchase_price=float(data["purchase_price"]),
        selling_price=float(data["selling_price"]),
        market_price=float(data["market_price"]),
        cryptomarket_id=int(data["cryptomarket_id"])
    )
    session.add(obj)
    await session.commit()


async def orm_get_cryptocurrencies(session: AsyncSession):
    result = await session.execute(select(Cryptocurrency))
    return result.scalars().all()


async def orm_get_cryptocurrency_by_cryptomarket_id(session: AsyncSession, cryptomarket_id: int):
    result = await session.execute(select(Cryptocurrency).where(Cryptocurrency.cryptomarket_id == cryptomarket_id))
    return result.scalars().all()


async def orm_update_cryptocurrency(session: AsyncSession, cryptocurrency_id: int, data):
    query = update(Cryptocurrency).where(Cryptocurrency.id == cryptocurrency_id).values(
        name=data["name"],
        balance=data["balance"],
        purchase_price=data["purchase_price"],
        selling_price=data["selling_price"],
        market_price=data["market_price"]
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_cryptocurrency(session: AsyncSession, cryptocurrency_id: int):
    query = delete(Cryptocurrency).where(Cryptocurrency.id == cryptocurrency_id)
    await session.execute(query)
    await session.commit()

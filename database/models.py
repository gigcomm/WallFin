from sqlalchemy import Text, Float, Integer, String, BigInteger, Date, DECIMAL, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from finance.bank import BankLogic
from finance.market import StockMarketLogic, CryptoMarketLogic


class Base(DeclarativeBase):
    pass


class Banner(Base):
    __tablename__ = "banner"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    image: Mapped[str] = mapped_column(String(150), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class User(Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(150))

    bank: Mapped[list["Bank"]] = relationship(back_populates='user')
    stockmarket: Mapped[list["StockMarket"]] = relationship(back_populates="user")
    cryptomarket: Mapped[list["CryptoMarket"]] = relationship(back_populates="user")


class Bank(Base):
    __tablename__ = 'bank'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bank")

    account: Mapped[list["Account"]] = relationship(back_populates="bank")
    currency: Mapped[list["Currency"]] = relationship(back_populates="bank")
    deposit: Mapped[list["Deposit"]] = relationship(back_populates="bank")

    def to_logic(self):
        return BankLogic(bank_name=self.name, accounts=self.account, currencies=self.currency, deposits=self.deposit)


class Account(Base):
    __tablename__ = 'account'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='account')


class Currency(Base):
    __tablename__ = 'currency'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='currency')


class Deposit(Base):
    __tablename__ = 'deposit'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    deposit_term: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='deposit')


class StockMarket(Base):
    __tablename__ = 'stockmarket'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="stockmarket")

    share: Mapped[list["Share"]] = relationship(back_populates="stockmarket")
    fund: Mapped[list["Fund"]] = relationship(back_populates="stockmarket")

    def to_logic(self):
        return StockMarketLogic(name=self.name, shares=self.share, funds=self.fund)


class Share(Base):
    __tablename__ = 'share'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stockmarket_id: Mapped[int] = mapped_column(ForeignKey("stockmarket.id", ondelete="CASCADE"), nullable=False)

    stockmarket: Mapped["StockMarket"] = relationship(back_populates="share")


class Fund(Base):
    __tablename__ = 'fund'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stockmarket_id: Mapped[int] = mapped_column(ForeignKey("stockmarket.id", ondelete="CASCADE"), nullable=False)

    stockmarket: Mapped["StockMarket"] = relationship(back_populates="fund")


class CryptoMarket(Base):
    __tablename__ = 'cryptomarket'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates='cryptomarket')

    cryptocurrency: Mapped[list["Cryptocurrency"]] = relationship(back_populates="cryptomarket")

    def to_logic(self):
        return CryptoMarketLogic(name=self.name, cryptocurrencies=self.cryptocurrency)


class Cryptocurrency(Base):
    __tablename__ = 'cryptocurrency'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    selling_price: Mapped[float] = mapped_column(Float, nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    cryptomarket_id: Mapped[int] = mapped_column(ForeignKey("cryptomarket.id", ondelete="CASCADE"), nullable=False)

    cryptomarket: Mapped["CryptoMarket"] = relationship(back_populates="cryptocurrency")

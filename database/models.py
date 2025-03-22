from sqlalchemy import Text, Float, Integer, String, BigInteger, Date, DECIMAL, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from finance.bank import BankLogic, AccountLogic, CurrencyLogic, DepositLogic
from finance.market import StockMarketLogic, CryptoMarketLogic, ShareLogic, FundLogic, СryptocurrencyLogic


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
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="bank")

    account: Mapped[list["Account"]] = relationship(back_populates="bank")
    currency: Mapped[list["Currency"]] = relationship(back_populates="bank")
    deposit: Mapped[list["Deposit"]] = relationship(back_populates="bank")

    def to_logic(self):
        account_logic = [AccountLogic(account.name, account.balance)
                         for account in self.account]
        currency_logic = [CurrencyLogic(curr.name, curr.balance, curr.market_price)
                          for curr in self.currency]
        deposit_logic = [DepositLogic(deposit.name, deposit.start_date, deposit.deposit_term, deposit.interest_rate,
                                      deposit.balance) for deposit in self.deposit]
        return BankLogic(bank_name=self.name, accounts=account_logic, currencies=currency_logic, deposits=deposit_logic)


class Account(Base):
    __tablename__ = 'account'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='account')


class Currency(Base):
    __tablename__ = 'currency'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(3), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='currency')


class Deposit(Base):
    __tablename__ = 'deposit'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[Date] = mapped_column(Date, nullable=False)
    deposit_term: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_rate: Mapped[float] = mapped_column(Float, nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False, default=0.0)
    bank_id: Mapped[int] = mapped_column(ForeignKey("bank.id", ondelete="CASCADE"), nullable=False)

    bank: Mapped["Bank"] = relationship(back_populates='deposit')


class StockMarket(Base):
    __tablename__ = 'stockmarket'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="stockmarket")

    share: Mapped[list["Share"]] = relationship(back_populates="stockmarket")
    fund: Mapped[list["Fund"]] = relationship(back_populates="stockmarket")

    def to_logic(self):
        share_logic = [
            ShareLogic(share.name, share.purchase_price, share.selling_price, share.market_price, share.quantity, share.currency)
            for share in self.share]
        fund_logic = [
            FundLogic(fund.name, fund.purchase_price, fund.selling_price, fund.market_price, fund.quantity, fund.currency)
            for fund in self.fund]
        return StockMarketLogic(name=self.name, shares=share_logic, funds=fund_logic)


class Share(Base):
    __tablename__ = 'share'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    purchase_price: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False)
    selling_price: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    stockmarket_id: Mapped[int] = mapped_column(ForeignKey("stockmarket.id", ondelete="CASCADE"), nullable=False)

    stockmarket: Mapped["StockMarket"] = relationship(back_populates="share")


class Fund(Base):
    __tablename__ = 'fund'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    purchase_price: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False)
    selling_price: Mapped[float] = mapped_column(DECIMAL(20, 2), nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    stockmarket_id: Mapped[int] = mapped_column(ForeignKey("stockmarket.id", ondelete="CASCADE"), nullable=False)

    stockmarket: Mapped["StockMarket"] = relationship(back_populates="fund")


class CryptoMarket(Base):
    __tablename__ = 'cryptomarket'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates='cryptomarket')

    cryptocurrency: Mapped[list["Cryptocurrency"]] = relationship(back_populates="cryptomarket")

    def to_logic(self):
        cryptocurrency_logic = [
            СryptocurrencyLogic(cryptocur.name, cryptocur.balance, cryptocur.purchase_price, cryptocur.selling_price,
                                cryptocur.market_price) for cryptocur in self.cryptocurrency]
        return CryptoMarketLogic(name=self.name, cryptocurrencies=cryptocurrency_logic)


class Cryptocurrency(Base):
    __tablename__ = 'cryptocurrency'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(10), nullable=False)
    balance: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False, default=0.0)
    purchase_price: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    selling_price: Mapped[float] = mapped_column(DECIMAL(20, 8), nullable=False)
    market_price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    cryptomarket_id: Mapped[int] = mapped_column(ForeignKey("cryptomarket.id", ondelete="CASCADE"), nullable=False)

    cryptomarket: Mapped["CryptoMarket"] = relationship(back_populates="cryptocurrency")

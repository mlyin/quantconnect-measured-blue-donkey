# region imports
from AlgorithmImports import *
# endregion
import numpy as np

class MeasuredBlueDonkey(QCAlgorithm):

#Dynamic approach: change lookback level based on the securities volatility
#If volatility is high, want to look back further than when the volatility is low

    def Initialize(self):
        self.SetCash(100000) #initialize starting capital for backtesting purposes
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2022, 6, 20)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol #Using daily data SPY

        self.lookback = 20

        self.ceiling, self.floor = 30, 12

        self.initialStopRisk = 0.97 #Trading stop loss, indicates how close first stop loss will be to securities price
        self.trailingStopRisk = 0.9 #How close our trading will follow the stocks price

        self.Schedule.On(self.DateRules.EveryDay(self.symbol), \
            self.TimeRules.AfterMarketOpen(self.symbol, 15), \
                Action(self.OnMarketOpen))

    def OnData(self, data: Slice): #Called every time algorithm receives new data
        self.Plot("Chart", self.symbol, self.Securities[self.symbol].Close)

    def OnMarketOpen(self):
        close = self.History(self.symbol, 31, Resolution.Daily)["close"] #Close price
        todayVolatility = np.std(close[1:31])
        yesterdayVolatility = np.std(close[0:30])
        deltaVolatility = (todayVolatility - yesterdayVolatility) / todayVolatility
        self.lookback = round(self.lookback * (1 + deltaVolatility)) #increases when volatility increases, and vice versa

        if self.lookback > self.ceiling: #Check if its within limits, and if so do nothing
            self.lookback = self.ceiling
        elif self.lookback < self.floor:
            self.lookback = self.floor
        #check if breakout is happening
        self.high = self.History(self.symbol, self.lookback, Resolution.Daily)["high"]

        if not self.Securities[self.symbol].Invested and \
                self.Securities[self.symbol].Close >= max(self.high[:-1]):
            self.SetHoldings(self.symbol, 1)
            self.breakoutlvl = max(self.high[:-1])
            self.highestPrice = self.breakoutlvl

        if self.Securities[self.symbol].Invested:
            if not self.Transactions.GetOpenOrders(self.symbol): #Send stop loss order
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, \
                                        -self.Portfolio[self.symbol].Quantity, \
                                        self.initialStopRisk * self.breakoutlvl)
            if self.Securities[self.symbol].Close > self.highestPrice and \
                    self.initialStopRisk * self.breakoutlvl < self.Securities[self.symbol].Close * self.trailingStopRisk:
                self.highestPrice = self.Securities[self.symbol].Close #set new highest price
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[self.symbol].Close * self.trailingStopRisk
                self.stopMarketTicket.Update(updateFields)

                self.Debug(updateFields.StopPrice)
            self.Plot("Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))

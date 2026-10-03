/* Ordinary cost-aware cargo operation. Never force performance, HQ stage, time,
 * industry production, terrain, bank balance or simulation RNG. */
class TrainCatalogue extends AIController {
	built = false;
	grown = false;
	train = 0;
	function Save() { return {built = this.built, grown = this.grown, train = this.train}; }
	function Load(version, data) {
		if (data != null && "built" in data) this.built = data.built;
		if (data != null && "grown" in data) this.grown = data.grown;
		if (data != null && "train" in data) this.train = data.train;
	}
	function Require(ok, operation) { if (!ok) throw operation+": "+AIError.GetLastErrorString(); }
	function Start();
}

function TrainCatalogue::Start()
{
	try {
		this.Require(this.built,"observer requires completed ordinary cargo-service save");
		this.Require(AIVehicle.IsValidVehicle(this.train),"original operating train");
		if (!this.grown) {
			this.Require(AIVehicle.SendVehicleToDepot(this.train),"normal depot order");
			local found = false;
			for (local tick = 0; tick < 6000; tick += 10) {
				if (AIVehicle.IsStoppedInDepot(this.train)) { found = true; break; }
				this.Sleep(10);
			}
			this.Require(found,"operating train reaches its depot");
			local depot = AIVehicle.GetLocation(this.train), rail = AIRail.GetRailType(depot);
			local engines = AIEngineList(AIVehicle.VT_RAIL), selected = -1, cost = 0;
			for (local engine = engines.Begin(); !engines.IsEnd(); engine = engines.Next()) {
				if (AIEngine.IsWagon(engine) || !AIEngine.IsBuildable(engine) || !AIEngine.HasPowerOnRail(engine,rail) ||
					AIEngine.GetMaxSpeed(engine) < 96 || AIEngine.GetPower(engine) < 700) continue;
				local running = AIEngine.GetRunningCost(engine);
				AILog.Info("HQ_NATURAL_COST {\"engine\":"+engine+",\"running_cost\":"+running+",\"speed\":"+AIEngine.GetMaxSpeed(engine)+"}");
				if (selected < 0 || running < cost) { selected = engine; cost = running; }
			}
			this.Require(selected >= 0,"available costed locomotive");
			local old = this.train, replacement = AIVehicle.BuildVehicle(depot,selected);
			this.Require(AIVehicle.IsValidVehicle(replacement),"purchase selected ordinary locomotive");
			this.Require(AIOrder.CopyOrders(replacement,old),"copy unchanged operating orders");
			for (local wagon = AIVehicle.GetNumWagons(old)-1; wagon >= 1; --wagon) {
				if (!AIEngine.IsWagon(AIVehicle.GetWagonEngineType(old,wagon))) continue;
				this.Require(AIVehicle.MoveWagon(old,wagon,replacement,AIVehicle.GetNumWagons(replacement)-1),"retain original cargo wagon");
			}
			this.Require(AIVehicle.SellVehicle(old),"sell replaced high-running-cost locomotive");
			this.train = replacement;
			while (AIVehicle.GetNumWagons(this.train) < 9) {
				local wagon = AIVehicle.BuildVehicle(depot,35);
				this.Require(AIVehicle.IsValidVehicle(wagon),"purchase original wood wagon");
				this.Require(AIVehicle.MoveWagon(wagon,0,this.train,AIVehicle.GetNumWagons(this.train)-1),"couple wood wagon through four-argument public API");
			}
			/* Reduce needless interest while retaining an ordinary operating reserve.
			 * No company funding/max-loan setting or direct account change is used. */
			local loan = AICompany.GetLoanAmount(), interval = AICompany.GetLoanInterval();
			local surplus = AICompany.GetBankBalance(AICompany.COMPANY_SELF)-11000000;
			if (surplus > interval) {
				local repayment = (surplus/interval)*interval;
				if (repayment > loan) repayment = loan;
				this.Require(AICompany.SetLoanAmount(loan-repayment),"ordinary affordable loan repayment");
			}
			this.Require(AIVehicle.StartStopVehicle(this.train),"restart costed cargo service");
			this.grown = true;
			AILog.Info("HQ_NATURAL_SERVICE_GROWN {\"train\":"+this.train+",\"engine\":"+selected+",\"running_cost\":"+cost+",\"wood_wagons\":8,\"unchanged_orders\":true}");
		}
		local hq = AICompany.GetCompanyHQ(AICompany.COMPANY_SELF);
		if (!AIMap.IsValidTile(hq)) {
			for (local y = 8; y < AIMap.GetMapSizeY()-8 && !AIMap.IsValidTile(hq); ++y) {
				for (local x = 8; x < AIMap.GetMapSizeX()-8; ++x) {
					local tile = AIMap.GetTileIndex(x,y);
					if (!AITile.IsBuildableRectangle(tile,2,2) || AITile.GetSlope(tile) != AITile.SLOPE_FLAT ||
						AITile.GetSlope(tile+1) != AITile.SLOPE_FLAT || AITile.GetSlope(tile+AIMap.GetMapSizeX()) != AITile.SLOPE_FLAT ||
						AITile.GetSlope(tile+AIMap.GetMapSizeX()+1) != AITile.SLOPE_FLAT) continue;
					if (AICompany.BuildCompanyHQ(tile)) { hq = tile; break; }
				}
			}
		}
		this.Require(AIMap.IsValidTile(hq),"ordinary legal HQ site");
		AILog.Info("HQ_NATURAL_READY {\"hq_x\":"+AIMap.GetTileX(hq)+",\"hq_y\":"+AIMap.GetTileY(hq)+"}");
		local previous_date = -1, previous_rating = -1;
		while (true) {
			local date = AIDate.GetCurrentDate(), rating = AICompany.GetQuarterlyPerformanceRating(AICompany.COMPANY_SELF,1);
			if (date != previous_date || rating != previous_rating) {
				AILog.Info("HQ_NATURAL_ECONOMY {\"date\":"+date+",\"year\":"+AIDate.GetYear(date)+",\"month\":"+AIDate.GetMonth(date)+
					",\"rating\":"+rating+",\"income\":"+AICompany.GetQuarterlyIncome(AICompany.COMPANY_SELF,1)+
					",\"delivered\":"+AICompany.GetQuarterlyCargoDelivered(AICompany.COMPANY_SELF,1)+
					",\"cash\":"+AICompany.GetBankBalance(AICompany.COMPANY_SELF)+",\"loan\":"+AICompany.GetLoanAmount()+
					",\"profit_this_year\":"+AIVehicle.GetProfitThisYear(this.train)+",\"profit_last_year\":"+AIVehicle.GetProfitLastYear(this.train)+
					",\"hq_x\":"+AIMap.GetTileX(hq)+",\"hq_y\":"+AIMap.GetTileY(hq)+"}");
				previous_date = date; previous_rating = rating;
			}
			if (rating >= 170) {
				AILog.Info("HQ_NATURAL_UPGRADE_READY {\"rating\":"+rating+",\"hq_x\":"+AIMap.GetTileX(hq)+",\"hq_y\":"+AIMap.GetTileY(hq)+"}");
				while (true) this.Sleep(1000);
			}
			this.Sleep(32);
		}
	} catch (error) { AILog.Error("HQ_NATURAL_FAILED "+error); }
	while (true) this.Sleep(1000);
}

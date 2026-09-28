/* SPDX-License-Identifier: GPL-2.0-only */
/* No effect construction, crash-state writes or private simulation hooks. */
class CrashReview extends AIController {
	built = false;
	trains = null;
	x = 0;
	y = 0;
	function Save() { return {built=this.built,trains=this.trains,x=this.x,y=this.y}; }
	function Load(version,data) {
		if (data != null && "built" in data) { this.built=data.built; this.trains=data.trains; this.x=data.x; this.y=data.y; }
	}
	function Require(ok,operation) { if (!ok) throw operation+": "+AIError.GetLastErrorString(); }
	function Tile(dx,dy) { return AIMap.GetTileIndex(this.x+dx,this.y+dy); }
	function Start() {
		try {
			AIController.SetCommandDelay(1);
			if (this.built) {
				local crashed=false;
				for (local tick=0; tick<1800 && !crashed; tick+=2) {
					crashed=true;
					foreach (train in this.trains) crashed=crashed && AIVehicle.IsValidVehicle(train) && AIVehicle.GetState(train)==AIVehicle.VS_CRASHED;
					this.Sleep(2);
				}
				if (!crashed) throw "ordinary opposing trains did not both crash";
				local tile=AIVehicle.GetLocation(this.trains[0]);
				AILog.Info("CRASH_REVIEW_OBSERVED {\"x\":"+AIMap.GetTileX(tile)+",\"y\":"+AIMap.GetTileY(tile)+"}");
				while (true) this.Sleep(1000);
			}
			this.Require(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"fund crash-review company");
			AICompany.SetName("OpenTT3D Crash Review");
			local found=false;
			for (local y=8; y<AIMap.GetMapSizeY()-12 && !found; y+=8) for (local x=8; x<AIMap.GetMapSizeX()-48; x+=8) {
				local tile=AIMap.GetTileIndex(x,y);
				if (AITile.GetMinHeight(tile)<2 || !AITile.IsBuildableRectangle(tile,44,10)) continue;
				local levelled=AITile.LevelTiles(tile,AIMap.GetTileIndex(x+43,y+9));
				this.Require(levelled || AIError.GetLastError()==AITile.ERR_AREA_ALREADY_FLAT,"level ordinary review plateau");
				this.x=x; this.y=y; found=true; break;
			}
			if (!found) throw "no buildable opposing-train plateau";
			local height=AITile.GetMinHeight(this.Tile(1,4));
			for (local x=1; x<=40; ++x) this.Require(AITile.GetSlope(this.Tile(x,4))==AITile.SLOPE_FLAT && AITile.GetMinHeight(this.Tile(x,4))==height,"verify flat original track datum");
			local west=this.Tile(1,4),east=this.Tile(40,4),engine=AIController.GetSetting("review_engine");
			AIRail.SetCurrentRailType(AIEngine.GetRailType(engine));
			this.Require(AIRail.BuildRailDepot(west,this.Tile(2,4)),"build west depot");
			this.Require(AIRail.BuildRailDepot(east,this.Tile(39,4)),"build east depot");
			for (local x=2; x<40; ++x) this.Require(AIRail.BuildRailTrack(this.Tile(x,4),AIRail.RAILTRACK_NE_SW),"build un-signalled opposing route");
			/* Ordinary block boundaries let both trains depart before a player-like
			 * signal-removal command joins their occupied blocks. No force-proceed
			 * hook or crash/effect state is written. */
			this.Require(AIRail.BuildSignal(this.Tile(10,4),this.Tile(9,4),AIRail.SIGNALTYPE_NORMAL),"protect west departure block");
			this.Require(AIRail.BuildSignal(this.Tile(31,4),this.Tile(32,4),AIRail.SIGNALTYPE_NORMAL),"protect east departure block");
			this.trains=[AIVehicle.BuildVehicle(west,engine),AIVehicle.BuildVehicle(east,engine)];
			foreach (train in this.trains) this.Require(AIVehicle.IsValidVehicle(train),"build original locomotive");
			this.Require(AIOrder.AppendOrder(this.trains[0],east,AIOrder.OF_STOP_IN_DEPOT),"order opposite east depot");
			this.Require(AIOrder.AppendOrder(this.trains[1],west,AIOrder.OF_STOP_IN_DEPOT),"order opposite west depot");
			foreach (train in this.trains) this.Require(AIVehicle.StartStopVehicle(train),"start original opposing train");
			local departed=false;
			for (local tick=0; tick<64 && !departed; tick+=2) {
				departed=true;
				foreach (train in this.trains) departed=departed && AIVehicle.GetState(train)==AIVehicle.VS_RUNNING && AIVehicle.GetCurrentSpeed(train)>0;
				this.Sleep(2);
			}
			if (!departed) throw "both opposing trains must actually depart";
			this.Require(AIRail.RemoveSignal(this.Tile(10,4),this.Tile(9,4)),"remove west block signal through normal command");
			this.Require(AIRail.RemoveSignal(this.Tile(31,4),this.Tile(32,4)),"remove east block signal through normal command");
			this.built=true;
			AILog.Info("CRASH_REVIEW_READY {\"x\":"+this.x+",\"y\":"+this.y+",\"engine\":"+engine+",\"trains\":["+this.trains[0]+","+this.trains[1]+"],\"departure_speeds\":["+AIVehicle.GetCurrentSpeed(this.trains[0])+","+AIVehicle.GetCurrentSpeed(this.trains[1])+"]}");
		} catch (error) { AILog.Error("CRASH_REVIEW_FAILED "+error); }
		while (true) this.Sleep(1000);
	}
}

/* Reuse a preserved public-command rail/tunnel journey. Build one legal HQ on
 * the hill through NoAI; never change map bytes, terrain, clocks or HQ stage. */
class RailFixture extends AIController {
	built = false;
	function Save() { return {built = this.built}; }
	function Load(version, data) { if (data != null && "built" in data) this.built = data.built; }
	function Require(ok, operation) { if (!ok) throw operation+": "+AIError.GetLastErrorString(); }
	function Start();
}

function RailFixture::Start()
{
	try {
		this.Require(this.built,"preserved verified rail journey");
		local entrance = AIMap.GetTileIndex(75,16), end = AITunnel.GetOtherTunnelEnd(entrance);
		this.Require(AITunnel.IsTunnelTile(entrance) && AIMap.IsValidTile(end) && AIMap.GetTileY(end) == 16 && AIMap.GetTileX(end) == 83,
			"preserved actual electric tunnel endpoints");
		local hq = AIMap.GetTileIndex(78,16);
		this.Require(AITile.IsBuildableRectangle(hq,2,2),"legal HQ footprint above existing tunnel");
		local height = AITile.GetMinHeight(hq);
		for (local y = 16; y < 18; ++y) for (local x = 78; x < 80; ++x) {
			local tile = AIMap.GetTileIndex(x,y);
			this.Require(AITile.GetSlope(tile) == AITile.SLOPE_FLAT && AITile.GetMinHeight(tile) == height,
				"unchanged flat upper tunnel hill");
		}
		this.Require(AICompany.BuildCompanyHQ(hq),"normal legal HQ construction above bore");
		this.Require(AICompany.GetCompanyHQ(AICompany.COMPANY_SELF) == hq,"actual company HQ location");
		AILog.Info("HQ_NATURAL_READY {\"hq_x\":78,\"hq_y\":16,\"surface_height\":"+height+
			",\"tunnel_x\":75,\"tunnel_y\":16,\"tunnel_end_x\":83,\"tunnel_end_y\":16,\"surface_unchanged\":true}");
	} catch (error) { AILog.Error("HQ_NATURAL_FAILED "+error); }
	while (true) this.Sleep(1000);
}

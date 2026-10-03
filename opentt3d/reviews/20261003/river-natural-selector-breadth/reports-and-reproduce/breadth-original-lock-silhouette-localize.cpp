/* Diagnostic only: exact source mesh/camera around the rejected street pixels. */
#include "src/renderer3d/voxel_geometry.hpp"
#include "src/renderer3d/camera.hpp"
#include "src/3rdparty/nlohmann/json.hpp"
#include <fstream>
#include <iostream>
using namespace Renderer3D;
using json = nlohmann::json;

int main(int argc, char **argv)
{
	if (argc != 2) return 2;
	std::ifstream input(argv[1]);
	json data = json::parse(input);
	std::vector<VoxelMaterial> materials;
	for (const auto &entry : data.at("materials")) materials.push_back({entry.get<std::array<uint8_t,6>>()});
	json report = json::array();
	for (const std::string part : {"front", "rear"}) for (const std::string direction : {"ne", "nw"}) {
		std::string name = "lock_study_middle_"+direction+"_"+part+"_sea";
		const auto &entry = data.at("models").at(name);
		auto origin = entry.at("origin").get<std::array<float,3>>(), step = entry.at("cell_size").get<std::array<float,3>>();
		VoxelGrid grid(entry.at("size").get<std::array<int,3>>(),materials,{origin[0],origin[1],origin[2]},{step[0],step[1],step[2]});
		for (const auto &run : entry.at("runs")) {
			auto r = run.get<std::array<int,5>>();
			grid.Fill({r[0],r[1],r[2]},{r[0]+r[3],r[1]+1,r[2]+1},r[4]);
		}
		auto mesh = grid.Mesh();
		unsigned view = direction == "ne" ? 4 : 5;
		auto camera = StreetReviewCamera(mesh.low,mesh.high,256,256,view-4+1.5f);
		auto matrix = camera.Matrix();
		double pixel_x = direction == "ne" ? 57.5 : 198.5, pixel_y = 185.5;
		json nearby = json::array();
		for (size_t index = 0; index < mesh.vertices.size(); index += 3) {
			std::array<std::array<double,2>,3> screen{};
			json world = json::array(), projected = json::array();
			bool clipped = false;
			for (unsigned i = 0; i < 3; ++i) {
				auto point = mesh.vertices[index+i].position;
				auto relative = point-camera.focus;
				std::array<double,3> clip{};
				for (unsigned j = 0; j < 3; ++j) {
					unsigned row = j == 2 ? 3 : j;
					clip[j] = static_cast<double>(matrix[row])*relative.x+static_cast<double>(matrix[4+row])*relative.y+
						static_cast<double>(matrix[8+row])*relative.z+matrix[12+row];
				}
				clipped |= clip[2] <= camera.Near();
				screen[i] = {(clip[0]/clip[2]+1)*128,(1-clip[1]/clip[2])*128};
				world.push_back({point.x,point.y,point.z});
				projected.push_back({screen[i][0],screen[i][1],clip[2]});
			}
			if (clipped) continue;
			auto edge = [](auto a, auto b, auto p) { return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]); };
			double area = edge(screen[0],screen[1],screen[2]);
			if (area >= 0) continue;
			std::array<double,3> distances{};
			for (unsigned i = 0; i < 3; ++i) {
				auto a = screen[i], b = screen[(i+1)%3];
				distances[i] = -edge(a,b,std::array{pixel_x,pixel_y})/std::hypot(b[0]-a[0],b[1]-a[1]);
			}
			if (*std::min_element(distances.begin(),distances.end()) < -0.02) continue;
			json snaps = json::array();
			for (unsigned bits : {4U,8U,12U}) {
				double scale = std::ldexp(1.0,bits);
				auto positions = screen;
				for (auto &point : positions) for (auto &coordinate : point) coordinate = std::round(coordinate*scale)/scale;
				std::array<double,3> edges{};
				for (unsigned i = 0; i < 3; ++i) edges[i] = edge(positions[i],positions[(i+1)%3],std::array{pixel_x,pixel_y});
				snaps.push_back({{"bits",bits},{"edge_functions",edges},{"strictly_inside",*std::max_element(edges.begin(),edges.end()) < 0}});
			}
			const auto &vertex = mesh.vertices[index];
			nearby.push_back({{"triangle",index/3},{"palette",static_cast<unsigned>(vertex.texture.x*256)},
				{"world_vertices",world},{"projected_unrounded_vertices",projected},{"area",area},
				{"signed_inside_edge_distances_pixels",distances},{"strictly_inside_unrounded",*std::min_element(distances.begin(),distances.end()) > 0},
				{"snapping_hypotheses",snaps}});
		}
		report.push_back({{"model",name},{"view",view},{"pixel_centre",{pixel_x,pixel_y}},
			{"triangles",mesh.vertices.size()/3},{"camera_focus",{camera.focus.x,camera.focus.y,camera.focus.z}},
			{"bounds",{{mesh.low.x,mesh.low.y,mesh.low.z},{mesh.high.x,mesh.high.y,mesh.high.z}}},
			{"matrix_float_words",matrix},{"nearby_front_triangles",nearby}});
	}
	std::cout << json{{"observed_model_camera_mesh_cases",report},{"runtime_source_or_artwork_changed",false},{"approvals",0},
		{"scope","Read-only reconstruction using exact original runtime mesher and fixed review camera. Double evaluation of the stored float matrix and hypothetical fixed-point snapping locate sample-edge candidates; they are not measured GPU vertex output or an accepted renderer repair. No artwork, positions, cameras, masks or comparison tolerance changed."}}.dump(2) << '\n';
}

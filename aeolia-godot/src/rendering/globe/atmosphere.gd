class_name Atmosphere
extends MeshInstance3D

## Node3D script that creates a transparent atmosphere rim glow around the planet.
## The atmosphere is rendered as a slightly larger sphere with a Fresnel-based rim glow effect.
## Transparent in the center, bright blue-white at the edges.

const ATMOSPHERE_RADIUS: float = 1.025
const SPHERE_RINGS: int = 64
const SPHERE_RADIAL_SEGMENTS: int = 64


## Creates the atmosphere sphere mesh and applies the Fresnel rim glow shader.
func setup() -> void:
	# Create the sphere mesh with appropriate resolution
	var sphere_mesh = SphereMesh.new()
	sphere_mesh.radius = ATMOSPHERE_RADIUS
	sphere_mesh.height = ATMOSPHERE_RADIUS * 2.0
	sphere_mesh.radial_segments = SPHERE_RADIAL_SEGMENTS
	sphere_mesh.rings = SPHERE_RINGS

	# Set the mesh
	mesh = sphere_mesh

	# Create and apply the atmosphere shader material
	var material = ShaderMaterial.new()
	material.shader = _create_atmosphere_shader()

	# Set shader uniforms
	material.set_shader_parameter("atmosphere_color", Vector3(0.4, 0.6, 1.0))
	material.set_shader_parameter("intensity", 0.35)

	set_surface_override_material(0, material)


## Creates the Fresnel rim glow shader for the atmosphere.
## The shader uses the back face (cull_front) to create a rim effect only visible
## from outside the sphere.
func _create_atmosphere_shader() -> Shader:
	var shader_code = """
shader_type spatial;
render_mode unshaded, blend_add, cull_front;

uniform vec3 atmosphere_color : source_color = vec3(0.4, 0.6, 1.0);
uniform float intensity : hint_range(0.0, 1.0) = 0.6;

void fragment() {
	// Calculate Fresnel effect based on view angle to surface normal
	// pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0) creates a strong rim effect
	// at grazing angles and fades to 0 when looking straight at the surface
	float fresnel = pow(1.0 - abs(dot(NORMAL, VIEW)), 3.0);

	// Output the atmosphere color modulated by Fresnel effect
	ALBEDO = atmosphere_color * fresnel;
	ALPHA = fresnel * intensity;
}
"""

	var shader = Shader.new()
	shader.code = shader_code
	return shader

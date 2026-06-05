# %% [markdown]
# ## Make bathymetry binary file based on netCDF bathy file bahia01_expand_bat.nc
# 
# In this notebook we prepare a bathymetry file for MITgcm based on the bathymetry developed by Esteban Cruz of a semi circular bay with no shelf (only slope). The bay is 120 km long and has a maximum depth of 160 m. The maximum depth in the domain is 1000 m.
# 
# We will make a bathymetry for a domain of size nx = 272, ny = 320, and a horizontal spacing of approximately 2 km (a coarse bathymetry, the real dx is 1.983 km and dy is 2.327 km).
# 
# The model will have 40 z levels of varying dz (starting from 2 m at the surface and increasing in thickness by 10.45% with each level).
# 
# The next bathimetries will include an elongated domain alongshore of increasing dx (telescopic) to avoid recirculation since AS boundaries will be periodic, and longer cross-shelf distance.

# %%
from netCDF4 import Dataset
import cmocean as cmo
import matplotlib.pyplot as plt
import numpy as np
import scipy.interpolate as sci_interp

# %%
272/16

# %%

nc_file = 'bahia01_expand_bat.nc'

with Dataset(nc_file, 'r') as nbl:
    print(nbl.variables)

# %%
with Dataset(nc_file, 'r') as nbl:
    Xog = nbl.variables['X'][:].data
    Yog = nbl.variables['Y'][:].data
    Z = nbl.variables['Z_sm'][:].data

# %%
# Show corners of the original bathymetry
print(f'left x-limit is {np.min(Xog)} m, and right x-limit is {np.max(Xog)} m')
print(f'bottom y-limit is {np.min(Yog)} m, and top y-limit is {np.max(Yog)} m')

# %%
682000 +139E3


# %%
# Build x and y arrays for new bathymetry
# Set desired number of grid points along x and y
nx_center = 238 #De esta manera tenemos delX=2000 m
ny = 320
x_min_center = -238E3 # m
x_max_center =  238E3 # m
x_min_expand = - 843E3 # m
x_max_expand =  843E3 # m
y_min = -62E3-440E3 # m 
y_min_expand = -682000 # m
y_max = 139E3 # m

DelX=int((2*x_max_center)/nx_center)

# Crear dominios en las regiones exteriores (-4L a -2L y 2L a 4L) con crecimiento cuadrático
# Aseguramos que el primer incremento sea 20 m usando un factor adecuado 'k'.
k = DelX # Ajustamos k para que el primer incremento sea 20 m
# Crear el vector para la expansión del lado derecho de forma más eficiente
i_values = np.arange(1, int(np.sqrt((x_max_expand - x_max_center) / k)) + 1)
i_values_y = np.arange(1, int(np.sqrt((np.abs(y_min_expand) - np.abs(y_min)) / k)) + 1)
x_right = x_max_center + k * i_values**2
y_expand = y_min - (k * i_values_y**2)
# Crear el vector para la expansión del lado izquierdo al reflejar y ordenar
x_left = -np.flip(x_right)
y_expand = np.flip(y_expand)
# Quitar los valores que se superponen con el centro
#x_left = x_left[:-1]
#x_right = x_right[1:]
#y_expand = y_expand[:-1]
# Crear el centro del dominio
x_center = np.round(np.linspace(x_min_center, x_max_center, nx_center), decimals=1)

# Unir todas las regiones para formar el dominio completo en X
x_vect = np.concatenate((x_left, x_center, x_right))

y_center = np.round(np.linspace(y_min, y_max ,ny), decimals=1)
y_vect = np.concatenate((y_expand, y_center))
#y_vect = np.round(np.linspace(y_min, y_max ,ny), decimals=1)

# Create interp function from original x, y and depth
f_interp = sci_interp.interp2d(Xog[0,:], Yog[:,0], Z)

# Interpolate into desired x and y vectors
bathy = f_interp(x_vect,y_vect)

# %%
bathy.shape

# %%
#Necesitoamos que nx=272 y ny=320, entonces seccionamos bathy y y_vect
bathy=bathy[9:,:]
y_vect = y_vect[9:]
print(bathy.shape)
print(y_vect.shape)

# %%
y_vect[0]

# %%
# Plot interp bathymetry

fig, ax = plt.subplots(1,1,figsize=(9,7))
pc = ax.pcolormesh(x_vect/1000,y_vect/1000,bathy, cmap=cmo.cm.deep_r)
cb = plt.colorbar(pc)

ax.contour(x_vect/1000,y_vect/1000,-bathy, colors='0.5', levels=[250])
ax.contour(x_vect/1000,y_vect/1000,-bathy, colors='k', levels=[0])

cb.set_label('profundidad / m')
ax.set_xlabel('Distancia meriodional (km)')
ax.set_ylabel('Distancia zonal (km)')

ax.set_aspect(1)

# Save the plot as a PNG file
file_path = "dominio_bath.png"
plt.savefig(file_path, dpi=300)
file_path

# %%
# Check some cross-shelf profiles starting from the center of the bay (0 km)
for ii in range(120,186,8):
    plt.plot(y_vect[:]/1E3,bathy[:,ii], label=f'{x_vect[ii]/1E3:1.1f} km')
plt.legend()
plt.xlabel('Cross-shelf distance (km)')
plt.ylabel('Depth (m)')

# %%
# Build grid spacing vectors dx and dy 
delx = x_vect[1:]-x_vect[:-1]
dely = y_vect[1:]-y_vect[:-1]
dx = np.append(delx, [delx[-1]], axis=0) # This is not the best way to do this
dy = np.append(dely, [dely[-1]], axis=0)

#Check values:
print(dx)
print(dy)

# %%
# Set filenames for binary files and data type
#bathy_fname = 'bahia_01_noShelf_bat.bin'
#dx_fname = 'bahia_01_noShelf_dx.bin'
#dy_fname = 'bahia_01_noShelf_dy.bin'
#dt = np.dtype('>f8')  # float 64 big endian

# %%
len(dx)

# %%
bathy_fname = 'bahia_01_expand_bat.bin'
dx_fname = 'bahia_01_expand_dx.bin'
dy_fname = 'bahia_01_expand_dy.bin'
dt = np.dtype('>f8')  # float 64 big endian

# %%
# Save binary files for dx, dy, bathy
fileobj = open(dx_fname,mode='wb')
dx.astype(dt).tofile(fileobj,"")
fileobj.close()

fileobj = open(dy_fname, mode='wb')
dy.astype(dt).tofile(fileobj,"")
fileobj.close()

fileobj = open(bathy_fname, mode='wb')
dd=bathy
dd.astype(dt).tofile(fileobj,"")
fileobj.close()

# Quick check
plt.pcolor(dd, cmap=cmo.cm.deep_r)
plt.colorbar()
plt.contour(dd, levels=[-1,0], colors='k')
plt.show()

# %%
# Check it is read correctly
cc=np.fromfile(bathy_fname, dtype=dt)
np.shape(cc)

nx= len(x_vect)
ny= len(y_vect)
bF=np.reshape(cc,[nx,ny],'F') # F to read in Fortran order

fig,ax = plt.subplots(1,1, figsize=(5,5))

pc = ax.pcolormesh(bF, cmap=cmo.cm.deep_r)
plt.colorbar(pc,ax=ax)
ax.contour(bF, levels=[-20,0], colors='k')

# %% [markdown]
# Yes, that is how it should look to go into MITgcm.

# %%


# %%


# %%
sNx =   17
sNy =   20
OLx =   3
OLy =   3
nSx =   8
nSy =   8
nPx =   2
nPy =   2
Nx  = sNx*nSx*nPx 
Ny  = sNy*nSy*nPy

# %%
320/16

# %%
Nx

# %%
Ny

# %%


# %%


# %%




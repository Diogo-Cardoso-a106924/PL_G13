program commonmain
  integer x, y, z
  real r
  common /numbers/ x, y
  common /numbers/ z
  common / / r
  x = 1
  y = 2
  z = 3
  r = 4.0
  print *, x, y, z
  print *, r
end

subroutine commonsub
  integer i, j, k
  real q
  common /numbers/ i, j
  common /numbers/ k
  common / / q
end

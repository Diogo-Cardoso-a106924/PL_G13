program datatest
  integer i, j, n
  integer a(4)
  real x, y
  logical ok
  data i, j / 7, 8 /
  data n, x / 1, 2.5 /
  data ok / .true. /
  data a / 4*0 /
  data a(2) / 99 /
  print *, i, j, n
  print *, x
  print *, ok
  print *, a(1), a(2), a(3), a(4)
end

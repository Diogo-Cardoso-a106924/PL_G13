program arith_basic
  integer a, b, c
  real x, y, z

  a = 10
  b = 3
  c = a + b
  c = a - b
  c = a * b
  c = a / b
  c = -a
  x = 2.5
  y = 1.5
  z = x + y
  z = x - y
  z = x * y
  z = x / y
  z = -x
  z = x ** 2
  z = x ** y
  a = a ** 2
  c = (a + b) * (a - b)
  z = (x + y) / (x - y)
  c = a + b * 2 - 1
  z = x * y + 2.0 / y - x
  print *, a
  print *, b
  print *, c
  print *, z
end

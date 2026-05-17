program compops
  integer a, b
  logical r1, r2, r3, r4, r5, r6
  a = 5
  b = 10
  r1 = a .EQ. b
  r2 = a .NE. b
  r3 = a .LT. b
  r4 = a .LE. b
  r5 = a .GT. b
  r6 = a .GE. b
  print *, r1
  print *, r2
  print *, r3
  print *, r4
  print *, r5
  print *, r6
end

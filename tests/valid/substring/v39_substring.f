program substring_test
  character*10 s, t
  integer i, j
  s = 'abcdefghij'
  i = 2
  j = 5
  t = s(i:j)
  s(1:3) = 'XYZ'
  print *, t
  print *, s(1:5)
end

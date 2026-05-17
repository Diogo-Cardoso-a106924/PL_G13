program nesteddo
  integer i, j, s
  s = 0
  do 20 i = 1, 3
    do 10 j = 1, 3
      s = s + 1
10  continue
20 continue
  print *, s
end

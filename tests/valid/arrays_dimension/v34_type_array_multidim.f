program typedmatrix
  integer i, j
  integer a(2, 3)
  do 10 i = 1, 2
    do 15 j = 1, 3
      a(i, j) = i * 10 + j
15  continue
10 continue
  print *, a(2, 2)
end

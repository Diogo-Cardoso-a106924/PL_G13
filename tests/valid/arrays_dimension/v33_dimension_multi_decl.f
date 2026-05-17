program dimmulti
  integer i, j, s
  dimension rows(3), mat(2, 4), tmp(10)
  s = 0
  do 10 i = 1, 3
    rows(i) = i
10 continue
  do 20 i = 1, 2
    do 15 j = 1, 4
      mat(i, j) = i + j
15  continue
20 continue
  print *, rows(1), mat(2, 3), tmp(1)
end

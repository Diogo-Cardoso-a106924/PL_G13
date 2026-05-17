program subtest
  integer a, b
  a = 10
  b = 20
  call swap(a, b)
  print *, a
  print *, b
end

subroutine swap(x, y)
  integer x, y, tmp
  tmp = x
  x = y
  y = tmp
  return
end

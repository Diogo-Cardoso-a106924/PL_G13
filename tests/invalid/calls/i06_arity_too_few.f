program badaritylow
  integer x
  x = 5
  call swap(x)
  print *, x
end

subroutine swap(a, b)
  integer a, b, tmp
  tmp = a
  a = b
  b = tmp
  return
end

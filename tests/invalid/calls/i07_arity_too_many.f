program badarityhigh
  integer x, y, z
  x = 1
  y = 2
  z = 3
  call inc(x, y, z)
  print *, x
end

subroutine inc(n)
  integer n
  n = n + 1
  return
end

program fwdref
  integer x
  x = 0
  call inc(x)
  print *, x
end

subroutine inc(n)
  integer n
  n = n + 1
  return
end

program functest
  integer n, r
  read *, n
  r = double(n)
  print *, r
end

integer function double(x)
  integer x
  double = x * 2
  return
end
